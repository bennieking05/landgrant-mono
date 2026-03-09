# NOTICE OF HEARING ON RESOLUTION OF NECESSITY

**{{ condemning_authority_name }}**

---

**Date of Notice:** {{ notice_date }}

**VIA {{ delivery_method | upper }}**

{{ owner_name }}
{{ owner_address_line1 }}
{{ owner_address_city }}, {{ owner_address_state }} {{ owner_address_zip }}

---

## NOTICE OF PROPOSED ACQUISITION BY EMINENT DOMAIN

**Re:** {{ project_name }}
Property: {{ property_address }}
Assessor's Parcel Number (APN): {{ parcel_apn }}{% if parcel_legal_description %}
Legal Description: {{ parcel_legal_description }}{% endif %}

---

Dear {{ owner_name }}:

**PLEASE TAKE NOTICE** that the {{ condemning_authority_name }}{% if condemning_authority_short %} ("{{ condemning_authority_short }}"){% endif %} is considering the adoption of a **Resolution of Necessity** to acquire certain real property interests in which you may have an interest. This notice is provided pursuant to California Code of Civil Procedure Section 1245.235.

---

## HEARING INFORMATION

| | |
|---|---|
| **Date:** | {{ hearing_date }} |
| **Time:** | {{ hearing_time }} |
| **Location:** | {{ hearing_location }} |
| | {{ hearing_address }} |
| | {{ hearing_city }}, {{ hearing_state }} {{ hearing_zip }} |

---

## PROPERTY TO BE ACQUIRED

**Property Description:**
{{ property_description }}

**Interest to be Acquired:**
{{ property_interest }}

**Project Purpose:**
{{ project_purpose }}

---

## YOUR RIGHTS

Under California law, you have the following rights in connection with this proceeding:

### 1. Right to Appear and Be Heard

You have the right to appear at the hearing and present evidence and testimony concerning:

- Whether the public interest and necessity require the project
- Whether the project is planned or located in a manner that will be most compatible with the greatest public good and cause the least private injury
- Whether the property described is necessary for the project

### 2. Right to Written Statement

You may file a written request with the {{ condemning_authority_short or condemning_authority_name }} asking for a statement of the reasons the acquisition is necessary. If you make such a request, we must provide the statement at least **20 days before the hearing**.

### 3. Right to Inspect Records

You have the right to inspect and copy public records related to this matter.

### 4. Right to Counsel

You may be represented by an attorney at the hearing.

---

## APPRAISAL AND OFFER

Pursuant to California Code of Civil Procedure Section 1245.230, an appraisal of your property has been conducted. Based on this appraisal, we have made or are making a written offer to acquire your property.

**Summary of Appraisal:**

| Item | Amount |
|------|--------|
{% if land_value %}| Land Value | ${{ land_value }} |{% endif %}
{% if improvements_value %}| Improvements | ${{ improvements_value }} |{% endif %}
{% if total_appraised_value %}| **Total Appraised Value** | **${{ total_appraised_value }}** |{% endif %}

{% if offer_amount %}**Current Offer Amount:** ${{ offer_amount }}{% endif %}

A copy of the appraisal summary {% if appraisal_enclosed %}is enclosed{% else %}is available upon request{% endif %}.

---

## RESOLUTION OF NECESSITY

If the {{ condemning_authority_short or condemning_authority_name }} adopts the Resolution of Necessity, it will make findings that:

1. **Public Interest and Necessity Require the Project** - The acquisition of your property is necessary for a public project that serves the public interest.

2. **Planned to Minimize Private Injury** - The project has been planned and located in a manner most compatible with the greatest public good and the least private injury.

3. **Property is Necessary for the Project** - The specific property described in this notice is necessary for the project.

---

## WHAT HAPPENS AFTER THE HEARING

**If the Resolution is Adopted:**

1. You may challenge the resolution by filing a writ of mandate within **30 days** of adoption (California Code of Civil Procedure Section 1250.370)
2. The {{ condemning_authority_short or condemning_authority_name }} may file a condemnation complaint in Superior Court
3. You will have the right to a jury trial to determine just compensation
4. If unable to reach agreement, the court will determine the fair market value of your property

**If the Resolution is NOT Adopted:**

- The {{ condemning_authority_short or condemning_authority_name }} cannot proceed with condemnation of your property for this project

---

## IMPORTANT DEADLINES

| Event | Deadline |
|-------|----------|
| Request for Statement of Reasons | At least 20 days before hearing |
| Hearing on Resolution | {{ hearing_date }} at {{ hearing_time }} |
| Challenge to Resolution (if adopted) | 30 days after adoption |

---

## QUESTIONS AND CONTACT

If you have any questions regarding this matter, please contact:

{{ contact_name }}{% if contact_title %}
{{ contact_title }}{% endif %}
{{ contact_department }}
{{ condemning_authority_name }}
{{ contact_address }}
{{ contact_city }}, {{ contact_state }} {{ contact_zip }}

Telephone: {{ contact_phone }}{% if contact_email %}
Email: {{ contact_email }}{% endif %}

---

## LEGAL CITATIONS

This notice is provided pursuant to:
- California Code of Civil Procedure Section 1245.235 (Notice requirements)
- California Code of Civil Procedure Section 1245.230 (Appraisal and offer requirements)
- California Code of Civil Procedure Section 1245.210 et seq. (Resolution of Necessity)

---

Respectfully,

**{{ condemning_authority_name | upper }}**

By: _____________________________
    {{ signatory_name }}
    {{ signatory_title }}

Date: {{ notice_date }}

---

## PROOF OF SERVICE

I declare under penalty of perjury that on {{ notice_date }}, I served a copy of this Notice on {{ owner_name }} by:

☐ Personal service
☐ Certified mail, return receipt requested, to the address shown above

_____________________________
Signature

_____________________________
Printed Name

---

*This notice does not constitute a taking of your property. The purpose of this notice is to inform you of your rights and the scheduled hearing on the proposed Resolution of Necessity. You are encouraged to consult with an attorney regarding your specific situation and rights under California law.*
