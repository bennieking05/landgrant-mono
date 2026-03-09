# ------------------------------------------------------------------------------
# Frontend Static Hosting - Cloud Storage (Direct Access)
# Cost-optimized: No Load Balancer or CDN for dev environment
# Access via: https://storage.googleapis.com/${bucket_name}/index.html
# ------------------------------------------------------------------------------

# Storage bucket for frontend static files
resource "google_storage_bucket" "frontend" {
  name                        = "${var.project_id}-frontend"
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

# Note: Public access disabled due to org policy (iam.allowedPolicyMemberDomains)
# For dev, access frontend via signed URLs or deploy to Firebase Hosting
# To enable public access, remove the org policy constraint or use a different project
#
# resource "google_storage_bucket_iam_member" "frontend_public" {
#   bucket = google_storage_bucket.frontend.name
#   role   = "roles/storage.objectViewer"
#   member = "allUsers"
# }

# ------------------------------------------------------------------------------
# Load Balancer + CDN for Custom Domain (app.landrightiq.com)
# Adds ~$18/month for global load balancer
# ------------------------------------------------------------------------------

# Static IP for frontend Load Balancer
resource "google_compute_global_address" "frontend_lb" {
  name    = "landright-frontend-ip"
  project = var.project_id

  depends_on = [time_sleep.wait_for_apis]
}

# SSL Certificate (Google-managed)
resource "google_compute_managed_ssl_certificate" "frontend" {
  name    = "landright-frontend-cert"
  project = var.project_id

  managed {
    domains = [var.app_domain]
  }

  depends_on = [time_sleep.wait_for_apis]
}

# Backend bucket with CDN
resource "google_compute_backend_bucket" "frontend" {
  name        = "landright-frontend-backend"
  project     = var.project_id
  bucket_name = google_storage_bucket.frontend.name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    default_ttl       = 3600
    max_ttl           = 86400
    negative_caching  = true
  }

  depends_on = [google_storage_bucket.frontend]
}

# URL map
resource "google_compute_url_map" "frontend" {
  name            = "landright-frontend-urlmap"
  project         = var.project_id
  default_service = google_compute_backend_bucket.frontend.id
}

# HTTPS proxy
resource "google_compute_target_https_proxy" "frontend" {
  name             = "landright-frontend-https"
  project          = var.project_id
  url_map          = google_compute_url_map.frontend.id
  ssl_certificates = [google_compute_managed_ssl_certificate.frontend.id]
}

# Forwarding rule (HTTPS)
resource "google_compute_global_forwarding_rule" "frontend_https" {
  name       = "landright-frontend-https-rule"
  project    = var.project_id
  target     = google_compute_target_https_proxy.frontend.id
  port_range = "443"
  ip_address = google_compute_global_address.frontend_lb.address
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "frontend_redirect" {
  name    = "landright-frontend-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect = true
    strip_query    = false
  }
}

resource "google_compute_target_http_proxy" "frontend_redirect" {
  name    = "landright-frontend-http-redirect"
  project = var.project_id
  url_map = google_compute_url_map.frontend_redirect.id
}

resource "google_compute_global_forwarding_rule" "frontend_http" {
  name       = "landright-frontend-http-rule"
  project    = var.project_id
  target     = google_compute_target_http_proxy.frontend_redirect.id
  port_range = "80"
  ip_address = google_compute_global_address.frontend_lb.address
}
