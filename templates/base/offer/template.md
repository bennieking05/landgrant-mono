## {{ offer_type_title }}

{% include "header" %}

{{ formatted_date }}

{{ owner_name }}
{{ owner_address_line1 }}
{{ owner_address_city }}, {{ owner_address_state }} {{ owner_address_zip }}

RE: {{ project_name }}
Parcel: {{ parcel_id }}{% if parcel_local_number %} (Local: {{ parcel_local_number }}){% endif %}

Dear {{ owner_salutation }}{{ owner_name }},

{% if jurisdiction == 'TX' %}
Pursuant to the Texas Property Code and your rights under the Landowner's Bill of Rights (enclosed), {{ condemning_authority_name }} hereby presents this {{ offer_type }} for the acquisition of property interests in connection with the {{ project_name }} project.

As required by Texas law, we have provided you with a Landowner's Bill of Rights document at least seven (7) days prior to this offer. Please review that document carefully as it explains your rights in this process.
{% elif jurisdiction == 'FL' %}
Pursuant to Florida Statutes Chapter 73 and your rights under Florida's Constitution, which guarantees "full compensation" for property taken for public use, {{ condemning_authority_name }} hereby presents this {{ offer_type }} for the acquisition of property interests in connection with the {{ project_name }} project.

Florida law requires that we make a good-faith effort to negotiate with you before any condemnation proceeding. This {{ offer_type }} represents our assessment based on a certified appraisal.
{% elif jurisdiction == 'IN' %}
Pursuant to Indiana Code 32-24, {{ condemning_authority_name }} hereby presents this {{ offer_type }} for the acquisition of property interests in connection with the {{ project_name }} project.

Under Indiana law, you have thirty (30) days from receipt of this offer to accept or reject it before we may proceed with condemnation proceedings.
{% elif jurisdiction == 'CA' %}
Pursuant to California Code of Civil Procedure Section 1230 et seq., {{ condemning_authority_name }} hereby presents this {{ offer_type }} for the acquisition of property interests in connection with the {{ project_name }} project.

A Resolution of Necessity public hearing {% if resolution_hearing_date %}is scheduled for {{ resolution_hearing_date }}{% else %}will be scheduled{% endif %}. You are entitled to receive notice of this hearing and to appear and present your objections.
{% elif jurisdiction == 'MI' %}
Pursuant to Michigan law (MCLA §213 et seq.) and the Michigan Constitution, {{ condemning_authority_name }} hereby presents this {{ offer_type }} for the acquisition of property interests in connection with the {{ project_name }} project.

{% if is_owner_occupied_residence %}Under the Michigan Constitution, you are entitled to receive 125% of the fair market value for your owner-occupied principal residence.{% endif %}

Please note that you have a limited time after any condemnation complaint is served to contest the necessity of the taking.
{% elif jurisdiction == 'MO' %}
Pursuant to Missouri Revised Statutes Chapter 523, {{ condemning_authority_name }} hereby presents this {{ offer_type }} for the acquisition of property interests in connection with the {{ project_name }} project.

{% if heritage_value_eligible %}Under Missouri law, you may be entitled to additional compensation (heritage value bonus) based on the length of family ownership of this property.{% endif %}

This offer is made following the required sixty (60) day notice of intent, and you have at least thirty (30) days to consider this final offer.
{% else %}
Pursuant to applicable state law, {{ condemning_authority_name }} hereby presents this {{ offer_type }} for the acquisition of property interests in connection with the {{ project_name }} project.
{% endif %}

---

## Property Interest to be Acquired

**Type of Interest:** {{ easement_type }}

**Purpose:** {{ easement_purpose }}

{% if legal_description %}
**Legal Description:** {{ legal_description }}
{% endif %}

---

## Compensation Offered

Based on a certified appraisal completed on {{ appraisal_date }}, we are authorized to offer the following compensation:

| Component | Amount |
|-----------|--------|
{% if permanent_easement_amount %}| Permanent Easement | ${{ permanent_easement_amount | number_format }} |
{% endif %}
{% if temporary_workspace_amount %}| Temporary Workspace | ${{ temporary_workspace_amount | number_format }} |
{% endif %}
{% if severance_damages_amount %}| Severance Damages | ${{ severance_damages_amount | number_format }} |
{% endif %}
{% if residence_multiplier_amount %}| Residence Multiplier ({{ residence_multiplier }}x) | ${{ residence_multiplier_amount | number_format }} |
{% endif %}
{% if heritage_bonus_amount %}| Heritage Value Bonus | ${{ heritage_bonus_amount | number_format }} |
{% endif %}
| **Total Compensation** | **${{ total_offer_amount | number_format }}** |

{% if includes_severance_damages %}
This amount includes compensation for any damage to your remaining property (severance damages).
{% endif %}

{% if jurisdiction == 'FL' %}
**Florida Full Compensation:** In addition to the above amount, if this matter proceeds to condemnation, Florida law requires the condemning authority to pay your reasonable attorney's fees, expert fees, appraisal fees, and costs. These fees do not reduce your compensation award.
{% endif %}

{% if jurisdiction == 'CA' and business_on_property %}
**Business Goodwill:** If you operate a business on this property, California law may entitle you to compensation for loss of business goodwill that cannot be avoided by relocating. Please consult with an attorney regarding this potential additional compensation.
{% endif %}

---

## Response Instructions

{% if response_window_days %}
You have **{{ response_window_days }} days** from receipt of this letter to respond. Please indicate your decision by:

- **Accepting** this offer by signing and returning the enclosed acceptance form
- **Countering** with a written counteroffer specifying your desired terms
- **Requesting a consultation** with our acquisition team to discuss the offer

{% endif %}

{% if jury_trial_available %}
**Your Right to a Jury Trial:** You have the right to a jury trial on the amount of just compensation if this matter proceeds to condemnation.
{% endif %}

{% if public_use_challenge_available %}
**Your Right to Challenge:** You have the right to challenge the public use or necessity of this taking in court within the time limits specified by law.
{% endif %}

---

## Contact Information

If you have questions about this offer or wish to schedule a meeting, please contact:

**{{ contact_name }}**{% if contact_title %}, {{ contact_title }}{% endif %}
{% if contact_company %}{{ contact_company }}{% endif %}
{{ contact_address }}
Phone: {{ contact_phone }}
{% if contact_email %}Email: {{ contact_email }}{% endif %}

---

{% if jurisdiction == 'TX' %}
**Important Texas Notice:** If you are dissatisfied with this offer, you have the right to request that the amount of compensation be determined by special commissioners appointed by the court, and to appeal that determination to a jury trial.
{% endif %}

{% if jurisdiction == 'MI' %}
**Important Michigan Notice:** The condemning authority is required by law to pay your reasonable attorney fees, expert fees, and litigation costs in this matter.
{% endif %}

Sincerely,

{{ signatory_name }}
{{ signatory_title }}
{{ condemning_authority_name }}

---

**Enclosures:**
{% if jurisdiction == 'TX' %}- Landowner's Bill of Rights
{% endif %}
- Appraisal Summary
- Project Description and Map
- Acceptance/Response Form
{% if jurisdiction == 'FL' %}- Florida Property Rights Brochure
{% endif %}
