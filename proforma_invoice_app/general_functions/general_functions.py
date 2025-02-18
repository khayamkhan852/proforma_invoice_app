import frappe
from frappe import _

def unlink_inter_company_doc(doctype, name, inter_company_reference):
	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		ref_doc = "Purchase Invoice" if doctype == "Sales Invoice" else "Sales Invoice"
		ref_field = "inter_company_invoice_reference"
	else:
		ref_doc = "Purchase Order" if doctype == "Sales Order" else "Sales Order"
		ref_field = "inter_company_order_reference"

	if inter_company_reference:
		frappe.db.set_value(doctype, name, ref_field, "")
		frappe.db.set_value(ref_doc, inter_company_reference, ref_field, "")
		
def update_linked_doc(doctype, name, inter_company_reference):
	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		ref_field = "inter_company_invoice_reference"
	else:
		ref_field = "inter_company_order_reference"

	if inter_company_reference:
		frappe.db.set_value(doctype, inter_company_reference, ref_field, name)


def validate_inter_company_party(doctype, party, company, inter_company_reference):
	if not party:
		return

	if doctype in ["Sales Invoice", "Sales Order", "Porforma"]:
		partytype, ref_partytype, internal = "Customer", "Supplier", "is_internal_customer"

		if doctype == "Sales Invoice":
			ref_doc = "Purchase Invoice"
		else:
			ref_doc = "Purchase Order"
	else:
		partytype, ref_partytype, internal = "Supplier", "Customer", "is_internal_supplier"

		if doctype == "Purchase Invoice":
			ref_doc = "Sales Invoice"
		else:
			ref_doc = "Proforma"

	if inter_company_reference:
		doc = frappe.get_doc(ref_doc, inter_company_reference)
		ref_party = doc.supplier if doctype in ["Sales Invoice", "Sales Order", "Proforma"] else doc.customer
		if not frappe.db.get_value(partytype, {"represents_company": doc.company}, "name") == party:
			frappe.throw(_("Invalid {0} for Inter Company Transaction.").format(_(partytype)))
		if not frappe.get_cached_value(ref_partytype, ref_party, "represents_company") == company:
			frappe.throw(_("Invalid Company for Inter Company Transaction."))

	elif frappe.db.get_value(partytype, {"name": party, internal: 1}, "name") == party:
		companies = frappe.get_all(
			"Allowed To Transact With",
			fields=["company"],
			filters={"parenttype": partytype, "parent": party},
		)
		companies = [d.company for d in companies]
		if company not in companies:
			frappe.throw(
				_("{0} not allowed to transact with {1}. Please change the Company.").format(
					_(partytype), company
				)
			)
