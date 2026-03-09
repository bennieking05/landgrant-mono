# INITIAL WRITTEN OFFER TO PURCHASE REAL PROPERTY

**{{ condemning_authority_name }}**{% if condemning_authority_short %} ("{{ condemning_authority_short }}"){% endif %}

---

**Date:** {{ service_date }}

**VIA CERTIFIED MAIL, RETURN RECEIPT REQUESTED**

{{ owner_name }}
{{ owner_address_line1 }}
{{ owner_address_city }}, {{ owner_address_state }} {{ owner_address_zip }}

**Re:** Offer to Purchase Property for {{ project_name }}
Property Address: {{ property_address }}
Parcel/Tax ID: {{ parcel_pin }}{% if parcel_legal_description %}
Legal Description: {{ parcel_legal_description }}{% endif %}

---

Dear {{ owner_name }}:

Pursuant to Texas Property Code Chapter 21 and specifically Section 21.0113, {{ condemning_authority_name }}{% if condemning_authority_short %} ("{{ condemning_authority_short }}"){% endif %} is hereby providing you with this written offer to acquire certain real property interests in connection with the {{ project_name }} project.

## OFFER SUMMARY

Based upon an appraisal prepared in accordance with Texas law, we are offering you the following compensation for your property:

| Item | Amount |
|------|--------|
| Land Value | ${{ land_value }} |
{% if improvements_value %}| Improvements | ${{ improvements_value }} |{% endif %}
{% if severance_damages %}| Severance Damages | ${{ severance_damages }} |{% endif %}
{% if temporary_easement_amount %}| Temporary Construction Easement | ${{ temporary_easement_amount }} |{% endif %}
| **TOTAL OFFER** | **${{ total_offer_amount }}** |

## PROPERTY INTERESTS TO BE ACQUIRED

{{ property_interest_description }}

## YOUR RIGHTS AND OPTIONS

**You are NOT required to accept this offer.** You have the right to:

1. **Negotiate** - You may make a counter-offer or negotiate for a higher amount
2. **Seek Professional Advice** - You may consult with an attorney, appraiser, or other professional at your expense
3. **Request Information** - You may request a copy of the appraisal upon which this offer is based

## IMPORTANT TIMELINES

- You have **at least {{ initial_offer_wait_days }} days** from the date of this offer before a final offer can be made
- If you do not respond, {{ condemning_authority_short or condemning_authority_name }} may proceed with a final offer and, ultimately, condemnation proceedings

## LANDOWNER'S BILL OF RIGHTS

Pursuant to Texas Property Code Section 21.0112, you should have received or will receive a Landowner's Bill of Rights document explaining your rights in this process. If you have not received this document, please contact us immediately.

## CONTACT INFORMATION

If you have any questions or wish to discuss this offer, please contact:

{{ contact_name }}{% if contact_title %}
{{ contact_title }}{% endif %}
{{ contact_company }}
{{ contact_address }}
Telephone: {{ contact_phone }}{% if contact_email %}
Email: {{ contact_email }}{% endif %}

---

## APPRAISAL DISCLOSURE

A copy of the appraisal upon which this offer is based {% if appraisal_enclosed %}is enclosed herewith{% else %}is available upon request{% endif %}. The appraisal was prepared by {{ appraiser_name }}{% if appraiser_certification %}, {{ appraiser_certification }}{% endif %}, dated {{ appraisal_date }}.

---

Respectfully submitted,

**{{ condemning_authority_name | upper }}**

By: _____________________________
    {{ signatory_name }}
    {{ signatory_title }}

Date: {{ service_date }}

---

## ACKNOWLEDGMENT OF RECEIPT

I/We acknowledge receipt of this Initial Written Offer on the _____ day of _____________, 20___.

_____________________________
{{ owner_name }}

---

*This offer is made pursuant to Texas Property Code Section 21.0113. Your failure to respond does not constitute acceptance or waiver of any rights.*
