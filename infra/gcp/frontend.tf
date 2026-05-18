# ------------------------------------------------------------------------------
# Frontend Static Hosting - Cloud Storage (Direct Access)
# Cost-optimized: No Load Balancer or CDN for dev environment
# Access via: https://storage.googleapis.com/${bucket_name}/index.html
# ------------------------------------------------------------------------------

# Storage bucket for frontend static files
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "google_storage_bucket" "frontend" {
  name                        = "${var.project_id}-frontend-${random_id.bucket_suffix.hex}"
  location                    = var.region
  project                     = var.project_id
  force_destroy               = true # Allow destroy for dev environment
  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html" # SPA fallback
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "OPTIONS"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  labels = local.common_labels

  depends_on = [time_sleep.wait_for_apis]
}

resource "google_storage_bucket_iam_member" "frontend_public" {
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"

  depends_on = [google_project_organization_policy.allow_public_access]
}

# ------------------------------------------------------------------------------
# Load Balancer + CDN for Custom Domain (app.landgrantiq.com)
# Adds ~$18/month for global load balancer
# ------------------------------------------------------------------------------

# Static IP for frontend Load Balancer
resource "google_compute_global_address" "frontend_lb" {
  name    = "landgrant-frontend-ip"
  project = var.project_id

  depends_on = [time_sleep.wait_for_apis]
}

# SSL Certificate (Google-managed)
# Bump `name` when domains change with create_before_destroy — GCP cert names are unique;
# reusing the same name causes 409 alreadyExists on create-before-destroy replacement.
# v4: removed apex_domain (now served by marketing Cloud Run with its own managed TLS)
resource "google_compute_managed_ssl_certificate" "frontend" {
  name    = "landgrant-frontend-cert-v4"
  project = var.project_id

  managed {
    domains = compact([var.app_domain, local.frontend_www_host])
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [time_sleep.wait_for_apis]
}

# Backend bucket with CDN
resource "google_compute_backend_bucket" "frontend" {
  name        = "landgrant-frontend-backend"
  project     = var.project_id
  bucket_name = google_storage_bucket.frontend.name
  enable_cdn  = true

  cdn_policy {
    cache_mode       = "CACHE_ALL_STATIC"
    default_ttl      = 3600
    max_ttl          = 86400
    negative_caching = true
  }

  depends_on = [google_storage_bucket.frontend]
}

# URL map
# Serves the SPA on app_domain. Apex is now handled by the marketing Cloud Run service.
# www still redirects to apex via this LB (browser follows redirect to Cloud Run marketing).
resource "google_compute_url_map" "frontend" {
  name    = "landgrant-frontend-urlmap"
  project = var.project_id

  default_service = google_compute_backend_bucket.frontend.id

  # www.example.com -> example.com (apex / marketing site on Cloud Run)
  dynamic "host_rule" {
    for_each = local.frontend_www_host != "" ? [1] : []
    content {
      hosts        = [local.frontend_www_host]
      path_matcher = "www-to-apex"
    }
  }

  dynamic "path_matcher" {
    for_each = local.frontend_www_host != "" ? [1] : []
    content {
      name = "www-to-apex"
      default_url_redirect {
        host_redirect          = var.apex_domain
        https_redirect         = true
        strip_query            = false
        redirect_response_code = "MOVED_PERMANENTLY_DEFAULT" # 301
      }
    }
  }
}

# HTTPS proxy
resource "google_compute_target_https_proxy" "frontend" {
  name             = "landgrant-frontend-https"
  project          = var.project_id
  url_map          = google_compute_url_map.frontend.id
  ssl_certificates = [google_compute_managed_ssl_certificate.frontend.id]
}

# Forwarding rule (HTTPS)
resource "google_compute_global_forwarding_rule" "frontend_https" {
  name       = "landgrant-frontend-https-rule"
  project    = var.project_id
  target     = google_compute_target_https_proxy.frontend.id
  port_range = "443"
  ip_address = google_compute_global_address.frontend_lb.address
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "frontend_redirect" {
  name    = "landgrant-frontend-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect = true
    strip_query    = false
  }
}

resource "google_compute_target_http_proxy" "frontend_redirect" {
  name    = "landgrant-frontend-http-redirect"
  project = var.project_id
  url_map = google_compute_url_map.frontend_redirect.id
}

resource "google_compute_global_forwarding_rule" "frontend_http" {
  name       = "landgrant-frontend-http-rule"
  project    = var.project_id
  target     = google_compute_target_http_proxy.frontend_redirect.id
  port_range = "80"
  ip_address = google_compute_global_address.frontend_lb.address
}
