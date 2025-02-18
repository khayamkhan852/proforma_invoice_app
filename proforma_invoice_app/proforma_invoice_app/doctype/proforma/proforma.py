# Copyright (c) 2025, Proforma Invoice App and contributors
# For license information, please see license.txt

import json
from typing import Literal

import frappe
import frappe.utils
from frappe import _, qb
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, cint, cstr, flt, get_link_to_form, getdate, nowdate, strip_html

from proforma_invoice_app.general_functions.general_functions import (
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)

from proforma_invoice_app.general_functions.party import get_party_account
from proforma_invoice_app.controllers.selling_controller import SellingController

from erpnext.manufacturing.doctype.blanket_order.blanket_order import (
	validate_against_blanket_order,
)
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
)
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	get_sre_reserved_qty_details_for_voucher,
	has_reserved_stock,
)

from proforma_invoice_app.general_functions.stock.utils import get_stock_balance
from proforma_invoice_app.general_functions.stock.get_item_details import get_bin_details, get_default_bom, get_price_list_rate
from proforma_invoice_app.general_functions.stock.stock_balance import get_reserved_qty, update_bin_qty

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}

class WarehouseRequired(frappe.ValidationError):
	pass


class Proforma(SellingController):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import (
			SalesTaxesandCharges,
		)

		from proforma_invoice_app.proforma_invoice_app.doctype.proforma_item.proforma_item import ProformaItem
		from erpnext.selling.doctype.sales_team.sales_team import SalesTeam
		from erpnext.stock.doctype.packed_item.packed_item import PackedItem

		additional_discount_percentage: DF.Float
		address_display: DF.SmallText | None
		advance_paid: DF.Currency
		advance_payment_status: DF.Literal["Not Requested", "Requested", "Partially Paid", "Fully Paid"]
		amended_from: DF.Link | None
		amount_eligible_for_commission: DF.Currency
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		auto_repeat: DF.Link | None
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.Data | None
		base_net_total: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		billing_status: DF.Literal["Not Billed", "Fully Billed", "Partly Billed", "Closed"]
		campaign: DF.Link | None
		commission_rate: DF.Float
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.SmallText | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		contact_phone: DF.Data | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		coupon_code: DF.Link | None
		currency: DF.Link
		customer: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		delivery_date: DF.Date | None
		delivery_status: DF.Literal[
			"Not Delivered", "Fully Delivered", "Partly Delivered", "Closed", "Not Applicable"
		]
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		dispatch_address: DF.SmallText | None
		dispatch_address_name: DF.Link | None
		from_date: DF.Date | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		inter_company_order_reference: DF.Link | None
		is_internal_customer: DF.Check
		items: DF.Table[ProformaItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		loyalty_amount: DF.Currency
		loyalty_points: DF.Int
		named_place: DF.Data | None
		naming_series: DF.Literal["PRO-INV-.YYYY.-"]
		net_total: DF.Currency
		order_type: DF.Literal["", "Sales", "Maintenance", "Shopping Cart"]
		other_charges_calculation: DF.TextEditor | None
		packed_items: DF.Table[PackedItem]
		party_account_currency: DF.Link | None
		payment_schedule: DF.Table[PaymentSchedule]
		payment_terms_template: DF.Link | None
		per_billed: DF.Percent
		per_delivered: DF.Percent
		per_picked: DF.Percent
		plc_conversion_rate: DF.Float
		po_date: DF.Date | None
		po_no: DF.Data | None
		price_list_currency: DF.Link
		pricing_rules: DF.Table[PricingRuleDetail]
		project: DF.Link | None
		represents_company: DF.Link | None
		reserve_stock: DF.Check
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		sales_partner: DF.Link | None
		sales_team: DF.Table[SalesTeam]
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		selling_price_list: DF.Link
		set_warehouse: DF.Link | None
		shipping_address: DF.SmallText | None
		shipping_address_name: DF.Link | None
		shipping_rule: DF.Link | None
		skip_delivery_note: DF.Check
		source: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"On Hold",
			"To Pay",
			"To Deliver and Bill",
			"To Bill",
			"To Deliver",
			"Completed",
			"Cancelled",
			"Closed",
		]
		tax_category: DF.Link | None
		tax_id: DF.Data | None
		taxes: DF.Table[SalesTaxesandCharges]
		taxes_and_charges: DF.Link | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		territory: DF.Link | None
		title: DF.Data | None
		to_date: DF.Date | None
		total: DF.Currency
		total_commission: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transaction_date: DF.Date
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def onload(self) -> None:
		super().onload()

		if frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
			if self.has_unreserved_stock():
				self.set_onload("has_unreserved_stock", True)

		if has_reserved_stock(self.doctype, self.name):
			self.set_onload("has_reserved_stock", True)

	def validate(self):
		# super().validate()
		self.validate_delivery_date()
		self.validate_proj_cust()
		self.validate_po()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_for_items()
		self.validate_warehouse()
		self.validate_drop_ship()
		self.validate_reserved_stock()
		self.validate_serial_no_based_delivery()
		validate_against_blanket_order(self)
		validate_inter_company_party(
			self.doctype, self.customer, self.company, self.inter_company_order_reference
		)

		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

			validate_coupon_code(self.coupon_code)

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

		make_packing_list(self)

		self.validate_with_previous_doc()
		self.set_status()

		if not self.billing_status:
			self.billing_status = "Not Billed"
		if not self.delivery_status:
			self.delivery_status = "Not Delivered"

		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def validate_po(self):
		# validate p.o date v/s delivery date
		if self.po_date and not self.skip_delivery_note:
			for d in self.get("items"):
				if d.delivery_date and getdate(self.po_date) > getdate(d.delivery_date):
					frappe.throw(
						_("Row #{0}: Expected Delivery Date cannot be before Purchase Order Date").format(
							d.idx
						)
					)

		if self.po_no and self.customer and not self.skip_delivery_note:
			so = frappe.db.sql(
				"select name from `tabProforma` \
				where ifnull(po_no, '') = %s and name != %s and docstatus < 2\
				and customer = %s",
				(self.po_no, self.name, self.customer),
			)
			if so and so[0][0]:
				if cint(
					frappe.db.get_single_value("Selling Settings", "allow_against_multiple_purchase_orders")
				):
					frappe.msgprint(
						_(
							"Warning: Proforma {0} already exists against Customer's Purchase Order {1}"
						).format(frappe.bold(so[0][0]), frappe.bold(self.po_no)),
						alert=True,
					)
				else:
					frappe.throw(
						_(
							"Proforma {0} already exists against Customer's Purchase Order {1}. To allow multiple Proformas, Enable {2} in {3}"
						).format(
							frappe.bold(so[0][0]),
							frappe.bold(self.po_no),
							frappe.bold(
								_("'Allow Multiple Proforma Against a Customer's Purchase Order'")
							),
							get_link_to_form("Selling Settings", "Selling Settings"),
						)
					)

	def validate_for_items(self):
		for d in self.get("items"):
			# used for production plan
			d.transaction_date = self.transaction_date

			tot_avail_qty = frappe.db.sql(
				"select projected_qty from `tabBin` \
				where item_code = %s and warehouse = %s",
				(d.item_code, d.warehouse),
			)
			d.projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0

	def product_bundle_has_stock_item(self, product_bundle):
		"""Returns true if product bundle has stock item"""
		ret = len(
			frappe.db.sql(
				"""select i.name from tabItem i, `tabProduct Bundle Item` pbi
			where pbi.parent = %s and pbi.item_code = i.name and i.is_stock_item = 1""",
				product_bundle,
			)
		)
		return ret

	def validate_sales_mntc_quotation(self):
		for d in self.get("items"):
			if d.prevdoc_docname:
				res = frappe.db.sql(
					"select name from `tabQuotation` where name=%s and order_type = %s",
					(d.prevdoc_docname, self.order_type),
				)
				if not res:
					frappe.msgprint(
						_("Quotation {0} not of type {1}").format(d.prevdoc_docname, self.order_type)
					)			

	def validate_delivery_date(self):
		if self.order_type == "Sales" and not self.skip_delivery_note:
			delivery_date_list = [d.delivery_date for d in self.get("items") if d.delivery_date]
			max_delivery_date = max(delivery_date_list) if delivery_date_list else None
			if (max_delivery_date and not self.delivery_date) or (
				max_delivery_date and getdate(self.delivery_date) != getdate(max_delivery_date)
			):
				self.delivery_date = max_delivery_date
			if self.delivery_date:
				for d in self.get("items"):
					if not d.delivery_date:
						d.delivery_date = self.delivery_date
					if getdate(self.transaction_date) > getdate(d.delivery_date):
						frappe.msgprint(
							_("Expected Delivery Date should be after Proforma Date"),
							indicator="orange",
							title=_("Invalid Delivery Date"),
							raise_exception=True,
						)
			else:
				frappe.throw(_("Please enter Delivery Date"))

		self.validate_sales_mntc_quotation()


	def validate_proj_cust(self):
		if self.project and self.customer_name:
			res = frappe.db.sql(
				"""select name from `tabProject` where name = %s
				and (customer = %s or ifnull(customer,'')='')""",
				(self.project, self.customer),
			)
			if not res:
				frappe.throw(
					_("Customer {0} does not belong to project {1}").format(self.customer, self.project)
				)


	def validate_warehouse(self):
		super().validate_warehouse()

		for d in self.get("items"):
			if (
				(
					frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1
					or (
						self.has_product_bundle(d.item_code)
						and self.product_bundle_has_stock_item(d.item_code)
					)
				)
				and not d.warehouse
				and not cint(d.delivered_by_supplier)
			):
				frappe.throw(
					_("Delivery warehouse required for stock item {0}").format(d.item_code), WarehouseRequired
				)

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Quotation": {"ref_dn_field": "prevdoc_docname", "compare_fields": [["company", "="]]},
				"Quotation Item": {
					"ref_dn_field": "quotation_item",
					"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
			}
		)

		if cint(frappe.db.get_single_value("Selling Settings", "maintain_same_sales_rate")):
			self.validate_rate_with_reference_doc([["Quotation", "prevdoc_docname", "quotation_item"]])

	def update_enquiry_status(self, prevdoc, flag):
		enq = frappe.db.sql(
			"select t2.prevdoc_docname from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.name=%s",
			prevdoc,
		)
		if enq:
			frappe.db.sql("update `tabOpportunity` set status = %s where name=%s", (flag, enq[0][0]))

	def update_prevdoc_status(self, flag=None):
		for quotation in set(d.prevdoc_docname for d in self.get("items")):
			if quotation:
				doc = frappe.get_doc("Quotation", quotation)
				if doc.docstatus.is_cancelled():
					frappe.throw(_("Quotation {0} is cancelled").format(quotation))

				doc.set_status(update=True)
				doc.update_opportunity("Converted" if flag == "submit" else "Quotation")

	def validate_drop_ship(self):
		for d in self.get("items"):
			if d.delivered_by_supplier and not d.supplier:
				frappe.throw(_("Row #{0}: Set Supplier for item {1}").format(d.idx, d.item_code))											

	def on_submit(self):
		self.check_credit_limit()
		self.update_reserved_qty()

		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)
		self.update_project()
		self.update_prevdoc_status("submit")

		self.update_blanket_order()

		update_linked_doc(self.doctype, self.name, self.inter_company_order_reference)
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "used")

		if self.get("reserve_stock"):
			self.create_stock_reservation_entries()

	def on_cancel(self):
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Payment Ledger Entry",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
		)
		super().on_cancel()

		# Cannot cancel closed SO
		if self.status == "Closed":
			frappe.throw(_("Closed invoice cannot be cancelled. Unclose to cancel."))

		self.check_nextdoc_docstatus()
		self.update_reserved_qty()
		self.update_project()
		self.update_prevdoc_status("cancel")

		self.db_set("status", "Cancelled")

		self.update_blanket_order()
		self.cancel_stock_reservation_entries()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_order_reference)
		if self.coupon_code:
			from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

			update_coupon_code_count(self.coupon_code, "cancelled")

	def update_project(self):
		if frappe.db.get_single_value("Selling Settings", "sales_update_frequency") != "Each Transaction":
			return

		if self.project:
			project = frappe.get_doc("Project", self.project)
			project.update_sales_amount()
			project.db_update()

	def check_credit_limit(self):
		# if bypass credit limit check is set to true (1) at Proforma level,
		# then we need not to check credit limit and vise versa
		if not cint(
			frappe.db.get_value(
				"Customer Credit Limit",
				{"parent": self.customer, "parenttype": "Customer", "company": self.company},
				"bypass_credit_limit_check",
			)
		):
			check_credit_limit(self.customer, self.company)

	def check_nextdoc_docstatus(self):
		linked_invoices = frappe.db.sql_list(
			"""select distinct t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.proforma = %s and t1.docstatus = 0""",
			self.name,
		)

		if linked_invoices:
			linked_invoices = [get_link_to_form("Sales Invoice", si) for si in linked_invoices]
			frappe.throw(
				_("Sales Invoice {0} must be deleted before cancelling this Proforma").format(
					", ".join(linked_invoices)
				)
			)

	def check_modified_date(self):
		mod_db = frappe.db.get_value("Proforma", self.name, "modified")
		date_diff = frappe.db.sql(f"select TIMEDIFF('{mod_db}', '{cstr(self.modified)}')")
		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)
		# Upon Proforma Re-open, check for credit limit.
		# Limit should be checked after the 'Hold/Closed' status is reset.
		if status == "Draft" and self.docstatus == 1:
			self.check_credit_limit()
		self.update_reserved_qty()
		self.notify_update()
		clear_doctype_notifications(self)

	def update_reserved_qty(self, so_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []

		def _valid_for_reserve(item_code, warehouse):
			if (
				item_code
				and warehouse
				and [item_code, warehouse] not in item_wh_list
				and frappe.get_cached_value("Item", item_code, "is_stock_item")
			):
				item_wh_list.append([item_code, warehouse])

		for d in self.get("items"):
			if (not so_item_rows or d.name in so_item_rows) and not d.delivered_by_supplier:
				if self.has_product_bundle(d.item_code):
					for p in self.get("packed_items"):
						if p.parent_detail_docname == d.name and p.parent_item == d.item_code:
							_valid_for_reserve(p.item_code, p.warehouse)
				else:
					_valid_for_reserve(d.item_code, d.warehouse)

		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {"reserved_qty": get_reserved_qty(item_code, warehouse)})

	def on_update(self):
		pass

	def on_update_after_submit(self):
		self.calculate_commission()
		self.calculate_contribution()
		self.check_credit_limit()

	def before_update_after_submit(self):
		self.validate_po()
		self.validate_drop_ship()
		self.validate_supplier_after_submit()
		self.validate_delivery_date()

	def validate_supplier_after_submit(self):
		"""Check that supplier is the same after submit if PO is already made"""
		exc_list = []

		for item in self.items:
			if item.supplier:
				supplier = frappe.db.get_value(
					"Proforma Item", {"parent": self.name, "item_code": item.item_code}, "supplier"
				)
				if item.ordered_qty > 0.0 and item.supplier != supplier:
					exc_list.append(
						_("Row #{0}: Not allowed to change Supplier as Purchase Order already exists").format(
							item.idx
						)
					)

		if exc_list:
			frappe.throw("\n".join(exc_list))				

	def update_delivery_status(self):
		"""Update delivery status from Purchase Order for drop shipping"""
		tot_qty, delivered_qty = 0.0, 0.0

		for item in self.items:
			if item.delivered_by_supplier:
				item_delivered_qty = frappe.db.sql(
					"""select sum(qty)
					from `tabPurchase Order Item` poi, `tabPurchase Order` po
					where poi.proforma_item = %s
						and poi.item_code = %s
						and poi.parent = po.name
						and po.docstatus = 1
						and po.status = 'Delivered'""",
					(item.name, item.item_code),
				)

				item_delivered_qty = item_delivered_qty[0][0] if item_delivered_qty else 0
				item.db_set("delivered_qty", flt(item_delivered_qty), update_modified=False)

			delivered_qty += item.delivered_qty
			tot_qty += item.qty

		if tot_qty != 0:
			self.db_set("per_delivered", flt(delivered_qty / tot_qty) * 100, update_modified=False)

	def update_picking_status(self):
		total_picked_qty = 0.0
		total_qty = 0.0
		per_picked = 0.0

		for so_item in self.items:
			if cint(
				frappe.get_cached_value("Item", so_item.item_code, "is_stock_item")
			) or self.has_product_bundle(so_item.item_code):
				total_picked_qty += flt(so_item.picked_qty)
				total_qty += flt(so_item.stock_qty)

		if total_picked_qty and total_qty:
			per_picked = total_picked_qty / total_qty * 100

			pick_percentage = frappe.db.get_single_value("Stock Settings", "over_picking_allowance")
			if pick_percentage:
				total_qty += flt(total_qty) * (pick_percentage / 100)

			if total_picked_qty > total_qty:
				frappe.throw(
					_(
						"Total Picked Quantity {0} is more than ordered qty {1}. You can set the Over Picking Allowance in Stock Settings."
					).format(total_picked_qty, total_qty)
				)

		self.db_set("per_picked", flt(per_picked), update_modified=False)

	def set_indicator(self):
		"""Set indicator for portal"""
		self.indicator_color = {
			"Draft": "red",
			"On Hold": "orange",
			"To Deliver and Bill": "orange",
			"To Bill": "orange",
			"To Deliver": "orange",
			"Completed": "green",
			"Cancelled": "red",
		}.get(self.status, "blue")

		self.indicator_title = _(self.status)

	def on_recurring(self, reference_doc, auto_repeat_doc):
		def _get_delivery_date(ref_doc_delivery_date, red_doc_transaction_date, transaction_date):
			delivery_date = auto_repeat_doc.get_next_schedule_date(schedule_date=ref_doc_delivery_date)

			if delivery_date <= transaction_date:
				delivery_date_diff = frappe.utils.date_diff(ref_doc_delivery_date, red_doc_transaction_date)
				delivery_date = frappe.utils.add_days(transaction_date, delivery_date_diff)

			return delivery_date

		self.set(
			"delivery_date",
			_get_delivery_date(
				reference_doc.delivery_date, reference_doc.transaction_date, self.transaction_date
			),
		)

		for d in self.get("items"):
			reference_delivery_date = frappe.db.get_value(
				"Proforma Item",
				{"parent": reference_doc.name, "item_code": d.item_code, "idx": d.idx},
				"delivery_date",
			)

			d.set(
				"delivery_date",
				_get_delivery_date(
					reference_delivery_date, reference_doc.transaction_date, self.transaction_date
				),
			)

	def validate_serial_no_based_delivery(self):
		reserved_items = []
		normal_items = []
		for item in self.items:
			if item.ensure_delivery_based_on_produced_serial_no:
				if item.item_code in normal_items:
					frappe.throw(
						_(
							"Cannot ensure delivery by Serial No as Item {0} is added with and without Ensure Delivery by Serial No."
						).format(item.item_code)
					)
				if item.item_code not in reserved_items:
					if not frappe.get_cached_value("Item", item.item_code, "has_serial_no"):
						frappe.throw(
							_(
								"Item {0} has no Serial No. Only serilialized items can have delivery based on Serial No"
							).format(item.item_code)
						)
					if not frappe.db.exists("BOM", {"item": item.item_code, "is_active": 1}):
						frappe.throw(
							_(
								"No active BOM found for item {0}. Delivery by Serial No cannot be ensured"
							).format(item.item_code)
						)
				reserved_items.append(item.item_code)
			else:
				normal_items.append(item.item_code)

			if not item.ensure_delivery_based_on_produced_serial_no and item.item_code in reserved_items:
				frappe.throw(
					_(
						"Cannot ensure delivery by Serial No as Item {0} is added with and without Ensure Delivery by Serial No."
					).format(item.item_code)
				)

	def validate_reserved_stock(self):
		"""Clean reserved stock flag for non-stock Item"""

		enable_stock_reservation = frappe.db.get_single_value("Stock Settings", "enable_stock_reservation")

		for item in self.items:
			if item.reserve_stock and (not enable_stock_reservation or not cint(item.is_stock_item)):
				item.reserve_stock = 0

	def has_unreserved_stock(self) -> bool:
		"""Returns True if there is any unreserved item in the Proforma."""

		reserved_qty_details = get_sre_reserved_qty_details_for_voucher("Proforma", self.name)

		for item in self.get("items"):
			if not item.get("reserve_stock"):
				continue

			unreserved_qty = get_unreserved_qty(item, reserved_qty_details)
			if unreserved_qty > 0:
				return True

		return False

	@frappe.whitelist()
	def create_stock_reservation_entries(
		self,
		items_details: list[dict] | None = None,
		from_voucher_type: Literal["Pick List", "Purchase Receipt"] = None,
		notify=True,
	) -> None:
		"""Creates Stock Reservation Entries for Proforma Items."""
		create_stock_reservation_entries_for_so_items(
			proforma=self,
			items_details=items_details,
			from_voucher_type=from_voucher_type,
			notify=notify,
		)

	@frappe.whitelist()
	def cancel_stock_reservation_entries(self, sre_list=None, notify=True) -> None:
		"""Cancel Stock Reservation Entries for Proforma Items."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)

		cancel_stock_reservation_entries(
			voucher_type=self.doctype, voucher_no=self.name, sre_list=sre_list, notify=notify
		)

def get_unreserved_qty(item: object, reserved_qty_details: dict) -> float:
	"""Returns the unreserved quantity for the Proforma Item."""

	existing_reserved_qty = reserved_qty_details.get(item.name, 0)
	return item.stock_qty - flt(item.delivered_qty) * item.get("conversion_factor", 1) - existing_reserved_qty


@frappe.whitelist()
def make_proforma(source_name: str, target_doc=None):
	if not frappe.db.get_singles_value(
		"Selling Settings", "allow_sales_order_creation_for_expired_quotation"
	):
		quotation = frappe.db.get_value(
			"Quotation", source_name, ["transaction_date", "valid_till"], as_dict=1
		)
		if quotation.valid_till and (
			quotation.valid_till < quotation.transaction_date or quotation.valid_till < getdate(nowdate())
		):
			frappe.throw(_("Validity period of this quotation has ended."))

	return _make_proforma(source_name, target_doc)

def _make_proforma(source_name, target_doc=None, ignore_permissions=False):
	customer = _make_customer(source_name, ignore_permissions)
	ordered_items = frappe._dict(
		frappe.db.get_all(
			"Proforma Item",
			{"prevdoc_docname": source_name, "docstatus": 1},
			["item_code", "sum(qty)"],
			group_by="item_code",
			as_list=1,
		)
	)

	selected_rows = [x.get("name") for x in frappe.flags.get("args", {}).get("selected_items", [])]

	def set_missing_values(source, target):
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

			# sales team
			if not target.get("sales_team"):
				for d in customer.get("sales_team") or []:
					target.append(
						"sales_team",
						{
							"sales_person": d.sales_person,
							"allocated_percentage": d.allocated_percentage or None,
							"commission_rate": d.commission_rate,
						},
					)

		if source.referral_sales_partner:
			target.sales_partner = source.referral_sales_partner
			target.commission_rate = frappe.get_value(
				"Sales Partner", source.referral_sales_partner, "commission_rate"
			)

		target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		balance_qty = obj.qty - ordered_items.get(obj.item_code, 0.0)
		target.qty = balance_qty if balance_qty > 0 else 0
		target.stock_qty = flt(target.qty) * flt(obj.conversion_factor)

		if obj.against_blanket_order:
			target.against_blanket_order = obj.against_blanket_order
			target.blanket_order = obj.blanket_order
			target.blanket_order_rate = obj.blanket_order_rate

	def can_map_row(item) -> bool:
		"""
		Row mapping from Quotation to Proforma:
		1. If no selections, map all non-alternative rows (that sum up to the grand total)
		2. If selections: Is Alternative Item/Has Alternative Item: Map if selected and adequate qty
		3. If selections: Simple row: Map if adequate qty
		"""
		has_qty = item.qty > 0

		if not selected_rows:
			return not item.is_alternative

		if selected_rows and (item.is_alternative or item.has_alternative_item):
			return (item.name in selected_rows) and has_qty

		# Simple row
		return has_qty

	doclist = get_mapped_doc(
		"Quotation",
		source_name,
		{
			"Quotation": {"doctype": "Proforma", "validation": {"docstatus": ["=", 1]}},
			"Quotation Item": {
				"doctype": "Proforma Item",
				"field_map": {"parent": "prevdoc_docname", "name": "quotation_item"},
				"postprocess": update_item,
				"condition": can_map_row,
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
			"Payment Schedule": {"doctype": "Payment Schedule", "add_if_empty": True},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)

	return doclist	

def _make_customer(source_name, ignore_permissions=False):
	quotation = frappe.db.get_value(
		"Quotation",
		source_name,
		["order_type", "quotation_to", "party_name", "customer_name"],
		as_dict=1,
	)

	if quotation.quotation_to == "Customer":
		return frappe.get_doc("Customer", quotation.party_name)

	# Check if a Customer already exists for the Lead or Prospect.
	existing_customer = None
	if quotation.quotation_to == "Lead":
		existing_customer = frappe.db.get_value("Customer", {"lead_name": quotation.party_name})
	elif quotation.quotation_to == "Prospect":
		existing_customer = frappe.db.get_value("Customer", {"prospect_name": quotation.party_name})

	if existing_customer:
		return frappe.get_doc("Customer", existing_customer)

	# If no Customer exists, create a new Customer or Prospect.
	if quotation.quotation_to == "Lead":
		return create_customer_from_lead(quotation.party_name, ignore_permissions=ignore_permissions)
	elif quotation.quotation_to == "Prospect":
		return create_customer_from_prospect(quotation.party_name, ignore_permissions=ignore_permissions)

	return None

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Orders"),
		}
	)

	return list_context

@frappe.whitelist()
def close_or_unclose_proforma(names, status):
	if not frappe.has_permission("Proforma", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	names = json.loads(names)
	for name in names:
		so = frappe.get_doc("Proforma", name)
		if so.docstatus == 1:
			if status == "Closed":
				if so.status not in ("Cancelled", "Closed") and (
					so.per_delivered < 100 or so.per_billed < 100
				):
					so.update_status(status)
			else:
				if so.status == "Closed":
					so.update_status("Draft")
			so.update_blanket_order()

	frappe.local.message_log = []

def get_requested_item_qty(proforma):
	result = {}
	for d in frappe.db.get_all(
		"Material Request Item",
		filters={"docstatus": 1, "proforma": proforma},
		fields=["proforma_item", "sum(qty) as qty", "sum(received_qty) as received_qty"],
		group_by="proforma_item",
	):
		result[d.proforma_item] = frappe._dict({"qty": d.qty, "received_qty": d.received_qty})

	return result

@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	requested_item_qty = get_requested_item_qty(source_name)

	def postprocess(source, target):
		if source.tc_name and frappe.db.get_value("Terms and Conditions", source.tc_name, "buying") != 1:
			target.tc_name = None
			target.terms = None

	def get_remaining_qty(so_item):
		return flt(
			flt(so_item.qty)
			- flt(requested_item_qty.get(so_item.name, {}).get("qty"))
			- max(
				flt(so_item.get("delivered_qty"))
				- flt(requested_item_qty.get(so_item.name, {}).get("received_qty")),
				0,
			)
		)

	def update_item(source, target, source_parent):
		# qty is for packed items, because packed items don't have stock_qty field
		target.project = source_parent.project
		target.qty = get_remaining_qty(source)
		target.stock_qty = flt(target.qty) * flt(target.conversion_factor)
		target.actual_qty = get_bin_details(
			target.item_code, target.warehouse, source_parent.company, True
		).get("actual_qty", 0)

		args = target.as_dict().copy()
		args.update(
			{
				"company": source_parent.get("company"),
				"price_list": frappe.db.get_single_value("Buying Settings", "buying_price_list"),
				"currency": source_parent.get("currency"),
				"conversion_rate": source_parent.get("conversion_rate"),
			}
		)

		target.rate = flt(
			get_price_list_rate(args=args, item_doc=frappe.get_cached_doc("Item", target.item_code)).get(
				"price_list_rate"
			)
		)
		target.amount = target.qty * target.rate

	doc = get_mapped_doc(
		"Proforma",
		source_name,
		{
			"Proforma": {"doctype": "Material Request", "validation": {"docstatus": ["=", 1]}},
			"Packed Item": {
				"doctype": "Material Request Item",
				"field_map": {"parent": "proforma", "uom": "stock_uom"},
				"postprocess": update_item,
			},
			"Proforma Item": {
				"doctype": "Material Request Item",
				"field_map": {"name": "proforma_item", "parent": "proforma"},
				"condition": lambda item: not frappe.db.exists(
					"Product Bundle", {"name": item.item_code, "disabled": 0}
				)
				and get_remaining_qty(item) > 0,
				"postprocess": update_item,
			},
		},
		target_doc,
		postprocess,
	)

	return doc

@frappe.whitelist()
def make_project(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.project_type = "External"
		doc.project_name = source.name

	doc = get_mapped_doc(
		"Proforma",
		source_name,
		{
			"Proforma": {
				"doctype": "Project",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {
					"name": "proforma",
					"base_grand_total": "estimated_costing",
					"net_total": "total_sales_amount",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doc

@frappe.whitelist()
def create_stock_reservation_entries_for_so_items(
	proforma: object,
	items_details: list[dict] | None = None,
	from_voucher_type: Literal["Pick List", "Purchase Receipt"] = None,
	notify=True,
) -> None:
	"""Creates Stock Reservation Entries for Proforma Items."""

	if not from_voucher_type and (
		proforma.get("_action") == "submit"
		and proforma.set_warehouse
		and cint(frappe.get_cached_value("Warehouse", proforma.set_warehouse, "is_group"))
	):
		return frappe.msgprint(
			_("Stock cannot be reserved in the group warehouse {0}.").format(
				frappe.bold(proforma.set_warehouse)
			)
		)

	validate_stock_reservation_settings(proforma)

	allow_partial_reservation = frappe.db.get_single_value("Stock Settings", "allow_partial_reservation")

	items = []
	if items_details:
		for item in items_details:
			so_item = frappe.get_doc("Proforma Item", item.get("proforma_item"))
			so_item.warehouse = item.get("warehouse")
			so_item.qty_to_reserve = (
				flt(item.get("qty_to_reserve"))
				if from_voucher_type in ["Pick List", "Purchase Receipt"]
				else (
					flt(item.get("qty_to_reserve"))
					* (flt(item.get("conversion_factor")) or flt(so_item.conversion_factor) or 1)
				)
			)
			so_item.from_voucher_no = item.get("from_voucher_no")
			so_item.from_voucher_detail_no = item.get("from_voucher_detail_no")
			so_item.serial_and_batch_bundle = item.get("serial_and_batch_bundle")

			items.append(so_item)

	sre_count = 0
	reserved_qty_details = get_sre_reserved_qty_details_for_voucher("Proforma", proforma.name)

	for item in items if items_details else proforma.get("items"):
		# Skip if `Reserved Stock` is not checked for the item.
		if not item.get("reserve_stock"):
			continue

		# Stock should be reserved from the Pick List if has Picked Qty.
		if not from_voucher_type == "Pick List" and flt(item.picked_qty) > 0:
			frappe.throw(
				_("Row #{0}: Item {1} has been picked, please reserve stock from the Pick List.").format(
					item.idx, frappe.bold(item.item_code)
				)
			)

		is_stock_item, has_serial_no, has_batch_no = frappe.get_cached_value(
			"Item", item.item_code, ["is_stock_item", "has_serial_no", "has_batch_no"]
		)

		# Skip if Non-Stock Item.
		if not is_stock_item:
			if not from_voucher_type:
				frappe.msgprint(
					_("Row #{0}: Stock cannot be reserved for a non-stock Item {1}").format(
						item.idx, frappe.bold(item.item_code)
					),
					title=_("Stock Reservation"),
					indicator="yellow",
				)

			item.db_set("reserve_stock", 0)
			continue

		# Skip if Group Warehouse.
		if frappe.get_cached_value("Warehouse", item.warehouse, "is_group"):
			frappe.msgprint(
				_("Row #{0}: Stock cannot be reserved in group warehouse {1}.").format(
					item.idx, frappe.bold(item.warehouse)
				),
				title=_("Stock Reservation"),
				indicator="yellow",
			)
			continue

		unreserved_qty = get_unreserved_qty(item, reserved_qty_details)

		# Stock is already reserved for the item, notify the user and skip the item.
		if unreserved_qty <= 0:
			if not from_voucher_type:
				frappe.msgprint(
					_("Row #{0}: Stock is already reserved for the Item {1}.").format(
						item.idx, frappe.bold(item.item_code)
					),
					title=_("Stock Reservation"),
					indicator="yellow",
				)

			continue

		available_qty_to_reserve = get_available_qty_to_reserve(item.item_code, item.warehouse)

		# No stock available to reserve, notify the user and skip the item.
		if available_qty_to_reserve <= 0:
			frappe.msgprint(
				_("Row #{0}: Stock not available to reserve for the Item {1} in Warehouse {2}.").format(
					item.idx, frappe.bold(item.item_code), frappe.bold(item.warehouse)
				),
				title=_("Stock Reservation"),
				indicator="orange",
			)
			continue

		# The quantity which can be reserved.
		qty_to_be_reserved = min(unreserved_qty, available_qty_to_reserve)

		if hasattr(item, "qty_to_reserve"):
			if item.qty_to_reserve <= 0:
				frappe.msgprint(
					_("Row #{0}: Quantity to reserve for the Item {1} should be greater than 0.").format(
						item.idx, frappe.bold(item.item_code)
					),
					title=_("Stock Reservation"),
					indicator="orange",
				)
				continue
			else:
				qty_to_be_reserved = min(qty_to_be_reserved, item.qty_to_reserve)

		# Partial Reservation
		if qty_to_be_reserved < unreserved_qty:
			if not from_voucher_type and (
				not item.get("qty_to_reserve") or qty_to_be_reserved < flt(item.get("qty_to_reserve"))
			):
				msg = _("Row #{0}: Only {1} available to reserve for the Item {2}").format(
					item.idx,
					frappe.bold(str(qty_to_be_reserved / item.conversion_factor) + " " + item.uom),
					frappe.bold(item.item_code),
				)
				frappe.msgprint(msg, title=_("Stock Reservation"), indicator="orange")

			# Skip the item if `Partial Reservation` is disabled in the Stock Settings.
			if not allow_partial_reservation:
				if qty_to_be_reserved == flt(item.get("qty_to_reserve")):
					msg = _(
						"Enable Allow Partial Reservation in the Stock Settings to reserve partial stock."
					)
					frappe.msgprint(msg, title=_("Partial Stock Reservation"), indicator="yellow")

				continue

		sre = frappe.new_doc("Stock Reservation Entry")

		sre.item_code = item.item_code
		sre.warehouse = item.warehouse
		sre.has_serial_no = has_serial_no
		sre.has_batch_no = has_batch_no
		sre.voucher_type = proforma.doctype
		sre.voucher_no = proforma.name
		sre.voucher_detail_no = item.name
		sre.available_qty = available_qty_to_reserve
		sre.voucher_qty = item.stock_qty
		sre.reserved_qty = qty_to_be_reserved
		sre.company = proforma.company
		sre.stock_uom = item.stock_uom
		sre.project = proforma.project

		if from_voucher_type:
			sre.from_voucher_type = from_voucher_type
			sre.from_voucher_no = item.from_voucher_no
			sre.from_voucher_detail_no = item.from_voucher_detail_no

		if item.get("serial_and_batch_bundle"):
			sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
			sre.reservation_based_on = "Serial and Batch"

			index, picked_qty = 0, 0
			while index < len(sbb.entries) and picked_qty < qty_to_be_reserved:
				entry = sbb.entries[index]
				qty = 1 if has_serial_no else min(abs(entry.qty), qty_to_be_reserved - picked_qty)

				sre.append(
					"sb_entries",
					{
						"serial_no": entry.serial_no,
						"batch_no": entry.batch_no,
						"qty": qty,
						"warehouse": entry.warehouse,
					},
				)

				index += 1
				picked_qty += qty

		sre.save()
		sre.submit()

		sre_count += 1

	if sre_count and notify:
		frappe.msgprint(_("Stock Reservation Entries Created"), alert=True, indicator="green")

@frappe.whitelist()
def validate_stock_reservation_settings(voucher: object) -> None:
	"""Raises an exception if `Stock Reservation` is not enabled or `Voucher Type` is not allowed."""

	if not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
		msg = _("Please enable {0} in the {1}.").format(
			frappe.bold(_("Stock Reservation")),
			frappe.bold(_("Stock Settings")),
		)
		frappe.throw(msg)

	# Voucher types allowed for stock reservation
	allowed_voucher_types = ["Proforma"]

	if voucher.doctype not in allowed_voucher_types:
		msg = _("Stock Reservation can only be created against {0}.").format(", ".join(allowed_voucher_types))
		frappe.throw(msg)

def get_available_qty_to_reserve(
	item_code: str, warehouse: str, batch_no: str | None = None, ignore_sre=None
) -> float:
	"""Returns `Available Qty to Reserve (Actual Qty - Reserved Qty)` for Item, Warehouse and Batch combination."""

	from erpnext.stock.doctype.batch.batch import get_batch_qty

	if batch_no:
		return get_batch_qty(
			item_code=item_code, warehouse=warehouse, batch_no=batch_no, ignore_voucher_nos=[ignore_sre]
		)

	available_qty = get_stock_balance(item_code, warehouse)

	if available_qty:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		query = (
			frappe.qb.from_(sre)
			.select(Sum(sre.reserved_qty - sre.delivered_qty))
			.where(
				(sre.docstatus == 1)
				& (sre.item_code == item_code)
				& (sre.warehouse == warehouse)
				& (sre.reserved_qty >= sre.delivered_qty)
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
		)

		if ignore_sre:
			query = query.where(sre.name != ignore_sre)

		reserved_qty = query.run()[0][0] or 0.0

		if reserved_qty:
			return available_qty - reserved_qty

	return available_qty

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
	from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
	from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
		get_sre_details_for_voucher,
		get_sre_reserved_qty_details_for_voucher,
		get_ssb_bundle_for_voucher,
	)

	if not kwargs:
		kwargs = {
			"for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
			"skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
		}

	kwargs = frappe._dict(kwargs)

	sre_details = {}
	if kwargs.for_reserved_stock:
		sre_details = get_sre_reserved_qty_details_for_voucher("Proforma", source_name)

	mapper = {
		"Proforma": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
		"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
		"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
	}

	def set_missing_values(source, target):
		if kwargs.get("ignore_pricing_rule"):
			# Skip pricing rule when the dn is creating from the pick list
			target.ignore_pricing_rule = 1

		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

		# if invoked in bulk creation, validations are ignored and thus this method is nerver invoked
		if frappe.flags.bulk_transaction:
			# set target items names to ensure proper linking with packed_items
			target.set_new_name()

		make_packing_list(target)

	def condition(doc):
		if doc.name in sre_details:
			del sre_details[doc.name]
			return False

		# make_mapped_doc sets js `args` into `frappe.flags.args`
		if frappe.flags.args and frappe.flags.args.delivery_dates:
			if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
				return False

		return abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = (
				frappe.db.get_value("Project", source_parent.project, "cost_center")
				or item.get("buying_cost_center")
				or item_group.get("buying_cost_center")
			)

	if not kwargs.skip_item_mapping:
		mapper["Proforma Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_proforma",
			},
			"condition": condition,
			"postprocess": update_item,
		}

	so = frappe.get_doc("Proforma", source_name)
	target_doc = get_mapped_doc("Proforma", so.name, mapper, target_doc)

	if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
		sre_list = get_sre_details_for_voucher("Proforma", source_name)

		if sre_list:

			def update_dn_item(source, target, source_parent):
				update_item(source, target, so)

			so_items = {d.name: d for d in so.items if d.stock_reserved_qty}

			for sre in sre_list:
				if not condition(so_items[sre.voucher_detail_no]):
					continue

				dn_item = get_mapped_doc(
					"Proforma Item",
					sre.voucher_detail_no,
					{
						"Proforma Item": {
							"doctype": "Delivery Note Item",
							"field_map": {
								"rate": "rate",
								"name": "so_detail",
								"parent": "against_proforma",
							},
							"postprocess": update_dn_item,
						}
					},
					ignore_permissions=True,
				)

				dn_item.qty = flt(sre.reserved_qty) * flt(dn_item.get("conversion_factor", 1))

				if sre.reservation_based_on == "Serial and Batch" and (sre.has_serial_no or sre.has_batch_no):
					dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre)

				target_doc.append("items", dn_item)
			else:
				# Correct rows index.
				for idx, item in enumerate(target_doc.items):
					item.idx = idx + 1

	# Should be called after mapping items.
	set_missing_values(so, target_doc)

	return target_doc

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		set_missing_values(source, target)
		# Get the advance paid Journal Entries in Sales Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

	def set_missing_values(source, target):
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

		# set the redeem loyalty points if provided via shopping cart
		if source.loyalty_points and source.order_type == "Shopping Cart":
			target.redeem_loyalty_points = 1

		target.debit_to = get_party_account("Customer", source.customer, source.company)

	def update_item(source, target, source_parent):
		target.amount = flt(source.amount) - flt(source.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = (
			target.amount / flt(source.rate)
			if (source.rate and source.billed_amt)
			else source.qty - source.returned_qty
		)

		if source_parent.project:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
		if target.item_code:
			item = get_item_defaults(target.item_code, source_parent.company)
			item_group = get_item_group_defaults(target.item_code, source_parent.company)
			cost_center = item.get("selling_cost_center") or item_group.get("selling_cost_center")

			if cost_center:
				target.cost_center = cost_center

	doclist = get_mapped_doc(
		"Proforma",
		source_name,
		{
			"Proforma": {
				"doctype": "Sales Invoice",
				"field_map": {
					"party_account_currency": "party_account_currency",
					"payment_terms_template": "payment_terms_template",
				},
				"field_no_map": ["payment_terms_template"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Proforma Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "so_detail",
					"parent": "proforma",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.qty
				and (doc.base_amount == 0 or abs(doc.billed_amt) < abs(doc.amount)),
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"reset_value": True,
			},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
		},
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)

	automatically_fetch_payment_terms = cint(
		frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)
	if automatically_fetch_payment_terms:
		doclist.set_payment_schedule()

	return doclist

@frappe.whitelist()
def make_maintenance_schedule(source_name, target_doc=None):
	maint_schedule = frappe.db.sql(
		"""select t1.name
		from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2
		where t2.parent=t1.name and t2.proforma=%s and t1.docstatus=1""",
		source_name,
	)

	if not maint_schedule:
		doclist = get_mapped_doc(
			"Proforma",
			source_name,
			{
				"Proforma": {"doctype": "Maintenance Schedule", "validation": {"docstatus": ["=", 1]}},
				"Proforma Item": {
					"doctype": "Maintenance Schedule Item",
					"field_map": {"parent": "proforma"},
				},
			},
			target_doc,
		)

		return doclist

@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None):
	visit = frappe.db.sql(
		"""select t1.name
		from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2
		where t2.parent=t1.name and t2.prevdoc_docname=%s
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""",
		source_name,
	)

	if not visit:
		doclist = get_mapped_doc(
			"Proforma",
			source_name,
			{
				"Proforma": {"doctype": "Maintenance Visit", "validation": {"docstatus": ["=", 1]}},
				"Proforma Item": {
					"doctype": "Maintenance Visit Purpose",
					"field_map": {"parent": "prevdoc_docname", "parenttype": "prevdoc_doctype"},
				},
			},
			target_doc,
		)

		return doclist

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions

	conditions = get_event_conditions("Proforma", filters)

	data = frappe.db.sql(
		f"""
		select
			distinct `tabProforma`.name, `tabProforma`.customer_name, `tabProforma`.status,
			`tabProforma`.delivery_status, `tabProforma`.billing_status,
			`tabProforma Item`.delivery_date
		from
			`tabProforma`, `tabProforma Item`
		where `tabProforma`.name = `tabProforma Item`.parent
			and `tabProforma`.skip_delivery_note = 0
			and (ifnull(`tabProforma Item`.delivery_date, '0000-00-00')!= '0000-00-00') \
			and (`tabProforma Item`.delivery_date between %(start)s and %(end)s)
			and `tabProforma`.docstatus < 2
			{conditions}
		""",
		{"start": start, "end": end},
		as_dict=True,
		update={"allDay": 0},
	)
	return data

@frappe.whitelist()
def make_purchase_order_for_default_supplier(source_name, selected_items=None, target_doc=None):
	"""Creates Purchase Order for each Supplier. Returns a list of doc objects."""

	from erpnext.setup.utils import get_exchange_rate

	if not selected_items:
		return

	if isinstance(selected_items, str):
		selected_items = json.loads(selected_items)

	def set_missing_values(source, target):
		target.supplier = supplier
		target.currency = frappe.db.get_value(
			"Supplier", filters={"name": supplier}, fieldname=["default_currency"]
		)
		company_currency = frappe.db.get_value(
			"Company", filters={"name": target.company}, fieldname=["default_currency"]
		)

		target.conversion_rate = get_exchange_rate(target.currency, company_currency, args="for_buying")

		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0
		target.inter_company_order_reference = ""
		target.shipping_rule = ""
		target.tc_name = ""
		target.terms = ""
		target.payment_terms_template = ""
		target.payment_schedule = []

		default_price_list = frappe.get_value("Supplier", supplier, "default_price_list")
		if default_price_list:
			target.buying_price_list = default_price_list

		default_payment_terms = frappe.get_value("Supplier", supplier, "payment_terms")
		if default_payment_terms:
			target.payment_terms_template = default_payment_terms

		if any(item.delivered_by_supplier == 1 for item in source.items):
			if source.shipping_address_name:
				target.shipping_address = source.shipping_address_name
				target.shipping_address_display = source.shipping_address
			else:
				target.shipping_address = source.customer_address
				target.shipping_address_display = source.address_display

			target.customer_contact_person = source.contact_person
			target.customer_contact_display = source.contact_display
			target.customer_contact_mobile = source.contact_mobile
			target.customer_contact_email = source.contact_email

		else:
			target.customer = ""
			target.customer_name = ""

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.schedule_date = source.delivery_date
		target.qty = flt(source.qty) - (flt(source.ordered_qty) / flt(source.conversion_factor))
		target.stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
		target.project = source_parent.project

	suppliers = [item.get("supplier") for item in selected_items if item.get("supplier")]
	suppliers = list(dict.fromkeys(suppliers))  # remove duplicates while preserving order

	items_to_map = [item.get("item_code") for item in selected_items if item.get("item_code")]
	items_to_map = list(set(items_to_map))

	if not suppliers:
		frappe.throw(_("Please set a Supplier against the Items to be considered in the Purchase Order."))

	purchase_orders = []
	for supplier in suppliers:
		doc = get_mapped_doc(
			"Proforma",
			source_name,
			{
				"Proforma": {
					"doctype": "Purchase Order",
					"field_no_map": [
						"address_display",
						"contact_display",
						"contact_mobile",
						"contact_email",
						"contact_person",
						"taxes_and_charges",
						"shipping_address",
					],
					"validation": {"docstatus": ["=", 1]},
				},
				"Proforma Item": {
					"doctype": "Purchase Order Item",
					"field_map": [
						["name", "proforma_item"],
						["parent", "proforma"],
						["stock_uom", "stock_uom"],
						["uom", "uom"],
						["conversion_factor", "conversion_factor"],
						["delivery_date", "schedule_date"],
					],
					"field_no_map": [
						"rate",
						"price_list_rate",
						"item_tax_template",
						"discount_percentage",
						"discount_amount",
						"pricing_rules",
					],
					"postprocess": update_item,
					"condition": lambda doc: doc.ordered_qty < doc.stock_qty
					and doc.supplier == supplier
					and doc.item_code in items_to_map,
				},
			},
			target_doc,
			set_missing_values,
		)

		doc.insert()
		frappe.db.commit()
		purchase_orders.append(doc)

	return purchase_orders

@frappe.whitelist()
def make_purchase_order(source_name, selected_items=None, target_doc=None):
	if not selected_items:
		return

	if isinstance(selected_items, str):
		selected_items = json.loads(selected_items)

	items_to_map = [
		item.get("item_code") for item in selected_items if item.get("item_code") and item.get("item_code")
	]
	items_to_map = list(set(items_to_map))

	def is_drop_ship_order(target):
		drop_ship = True
		for item in target.items:
			if not item.delivered_by_supplier:
				drop_ship = False
				break

		return drop_ship

	def set_missing_values(source, target):
		target.supplier = ""
		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0
		target.inter_company_order_reference = ""
		target.shipping_rule = ""
		target.tc_name = ""
		target.terms = ""
		target.payment_terms_template = ""
		target.payment_schedule = []

		if is_drop_ship_order(target):
			target.customer = source.customer
			target.customer_name = source.customer_name
			target.shipping_address = source.shipping_address_name
		else:
			target.customer = target.customer_name = target.shipping_address = None

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.schedule_date = source.delivery_date
		target.qty = flt(source.qty) - (flt(source.ordered_qty) / flt(source.conversion_factor))
		target.stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
		target.project = source_parent.project

	def update_item_for_packed_item(source, target, source_parent):
		target.qty = flt(source.qty) - flt(source.ordered_qty)

	# po = frappe.get_list("Purchase Order", filters={"sales_order":source_name, "supplier":supplier, "docstatus": ("<", "2")})
	doc = get_mapped_doc(
		"Proforma",
		source_name,
		{
			"Proforma": {
				"doctype": "Purchase Order",
				"field_no_map": [
					"address_display",
					"contact_display",
					"contact_mobile",
					"contact_email",
					"contact_person",
					"taxes_and_charges",
					"shipping_address",
				],
				"validation": {"docstatus": ["=", 1]},
			},
			"Proforma Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "proforma_item"],
					["parent", "proforma"],
					["stock_uom", "stock_uom"],
					["uom", "uom"],
					["conversion_factor", "conversion_factor"],
					["delivery_date", "schedule_date"],
				],
				"field_no_map": [
					"rate",
					"price_list_rate",
					"item_tax_template",
					"discount_percentage",
					"discount_amount",
					"supplier",
					"pricing_rules",
				],
				"postprocess": update_item,
				"condition": lambda doc: doc.ordered_qty < doc.stock_qty
				and doc.item_code in items_to_map
				and not is_product_bundle(doc.item_code),
			},
			"Packed Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "proforma_packed_item"],
					["parent", "proforma"],
					["uom", "uom"],
					["conversion_factor", "conversion_factor"],
					["parent_item", "product_bundle"],
					["rate", "rate"],
				],
				"field_no_map": [
					"price_list_rate",
					"item_tax_template",
					"discount_percentage",
					"discount_amount",
					"supplier",
					"pricing_rules",
				],
				"postprocess": update_item_for_packed_item,
				"condition": lambda doc: doc.parent_item in items_to_map,
			},
		},
		target_doc,
		set_missing_values,
	)

	set_delivery_date(doc.items, source_name)

	return doc

def set_delivery_date(items, proforma):
	delivery_dates = frappe.get_all(
		"Proforma Item", filters={"parent": proforma}, fields=["delivery_date", "item_code"]
	)

	delivery_by_item = frappe._dict()
	for date in delivery_dates:
		delivery_by_item[date.item_code] = date.delivery_date

	for item in items:
		if item.product_bundle:
			item.schedule_date = delivery_by_item[item.product_bundle]

def is_product_bundle(item_code):
	return frappe.db.exists("Product Bundle", {"name": item_code, "disabled": 0})			

@frappe.whitelist()
def make_work_orders(items, proforma, company, project=None):
	"""Make Work Orders against the given Proforma for the given `items`"""
	items = json.loads(items).get("items")
	out = []

	for i in items:
		if not i.get("bom"):
			frappe.throw(_("Please select BOM against item {0}").format(i.get("item_code")))
		if not i.get("pending_qty"):
			frappe.throw(_("Please select Qty against item {0}").format(i.get("item_code")))

		work_order = frappe.get_doc(
			dict(
				doctype="Work Order",
				production_item=i["item_code"],
				bom_no=i.get("bom"),
				qty=i["pending_qty"],
				company=company,
				proforma=proforma,
				proforma_item=i["proforma_item"],
				project=project,
				fg_warehouse=i["warehouse"],
				description=i["description"],
			)
		).insert()
		work_order.set_work_order_operations()
		work_order.flags.ignore_mandatory = True
		work_order.save()
		out.append(work_order)

	return [p.name for p in out]

@frappe.whitelist()
def update_status(status, name):
	so = frappe.get_doc("Proforma", name)
	so.update_status(status)

@frappe.whitelist()
def make_raw_material_request(items, company, proforma, project=None):
	if not frappe.has_permission("Proforma", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(items, str):
		items = frappe._dict(json.loads(items))

	for item in items.get("items"):
		item["include_exploded_items"] = items.get("include_exploded_items")
		item["ignore_existing_ordered_qty"] = items.get("ignore_existing_ordered_qty")
		item["include_raw_materials_from_sales_order"] = items.get("include_raw_materials_from_sales_order")

	items.update({"company": company, "proforma": proforma})

	raw_materials = get_items_for_material_requests(items)
	if not raw_materials:
		frappe.msgprint(_("Material Request not created, as quantity for Raw Materials already available."))
		return

	material_request = frappe.new_doc("Material Request")
	material_request.update(
		dict(
			doctype="Material Request",
			transaction_date=nowdate(),
			company=company,
			material_request_type="Purchase",
		)
	)
	for item in raw_materials:
		item_doc = frappe.get_cached_doc("Item", item.get("item_code"))

		schedule_date = add_days(nowdate(), cint(item_doc.lead_time_days))
		row = material_request.append(
			"items",
			{
				"item_code": item.get("item_code"),
				"qty": item.get("quantity"),
				"schedule_date": schedule_date,
				"warehouse": item.get("warehouse"),
				"proforma": proforma,
				"project": project,
			},
		)

		if not (strip_html(item.get("description")) and strip_html(item_doc.description)):
			row.description = item_doc.item_name or item.get("item_code")

	material_request.insert()
	material_request.flags.ignore_permissions = 1
	material_request.run_method("set_missing_values")
	material_request.submit()
	return material_request

@frappe.whitelist()
def make_inter_company_purchase_order(source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction

	return make_inter_company_transaction("Proforma", source_name, target_doc)

@frappe.whitelist()
def create_pick_list(source_name, target_doc=None):
	from erpnext.stock.doctype.packed_item.packed_item import is_product_bundle

	def validate_proforma():
		so = frappe.get_doc("Proforma", source_name)
		for item in so.items:
			if item.stock_reserved_qty > 0:
				frappe.throw(
					_(
						"Cannot create a pick list for Proforma {0} because it has reserved stock. Please unreserve the stock in order to create a pick list."
					).format(frappe.bold(source_name))
				)

	def update_item_quantity(source, target, source_parent) -> None:
		picked_qty = flt(source.picked_qty) / (flt(source.conversion_factor) or 1)
		qty_to_be_picked = flt(source.qty) - max(picked_qty, flt(source.delivered_qty))

		target.qty = qty_to_be_picked
		target.stock_qty = qty_to_be_picked * flt(source.conversion_factor)

	def update_packed_item_qty(source, target, source_parent) -> None:
		qty = flt(source.qty)
		for item in source_parent.items:
			if source.parent_detail_docname == item.name:
				picked_qty = flt(item.picked_qty) / (flt(item.conversion_factor) or 1)
				pending_percent = (item.qty - max(picked_qty, item.delivered_qty)) / item.qty
				target.qty = target.stock_qty = qty * pending_percent
				return

	def should_pick_order_item(item) -> bool:
		return (
			abs(item.delivered_qty) < abs(item.qty)
			and item.delivered_by_supplier != 1
			and not is_product_bundle(item.item_code)
		)

	# Don't allow a Pick List to be created against a Proforma that has reserved stock.
	validate_proforma()

	doc = get_mapped_doc(
		"Proforma",
		source_name,
		{
			"Proforma": {
				"doctype": "Pick List",
				"field_map": {"set_warehouse": "parent_warehouse"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Proforma Item": {
				"doctype": "Pick List Item",
				"field_map": {"parent": "proforma", "name": "proforma_item"},
				"postprocess": update_item_quantity,
				"condition": should_pick_order_item,
			},
			"Packed Item": {
				"doctype": "Pick List Item",
				"field_map": {
					"parent": "proforma",
					"name": "proforma_item",
					"parent_detail_docname": "product_bundle_item",
				},
				"field_no_map": ["picked_qty"],
				"postprocess": update_packed_item_qty,
			},
		},
		target_doc,
	)

	doc.purpose = "Delivery"

	doc.set_item_locations()

	return doc


def update_produced_qty_in_so_item(proforma, proforma_item):
	# for multiple work orders against same Proforma item
	linked_wo_with_so_item = frappe.db.get_all(
		"Work Order",
		["produced_qty"],
		{"proforma_item": proforma_item, "proforma": proforma, "docstatus": 1},
	)

	total_produced_qty = 0
	for wo in linked_wo_with_so_item:
		total_produced_qty += flt(wo.get("produced_qty"))

	if not total_produced_qty and frappe.flags.in_patch:
		return

	frappe.db.set_value("Proforma Item", proforma_item, "produced_qty", total_produced_qty)


@frappe.whitelist()
def get_work_order_items(proforma, for_raw_material_request=0):
	"""Returns items with BOM that already do not have a linked work order"""
	if proforma:
		so = frappe.get_doc("Proforma", proforma)

		wo = qb.DocType("Work Order")

		items = []
		item_codes = [i.item_code for i in so.items]
		product_bundle_parents = [
			pb.new_item_code
			for pb in frappe.get_all(
				"Product Bundle", {"new_item_code": ["in", item_codes], "disabled": 0}, ["new_item_code"]
			)
		]

		for table in [so.items, so.packed_items]:
			for i in table:
				bom = get_default_bom(i.item_code)
				stock_qty = i.qty if i.doctype == "Packed Item" else i.stock_qty

				if not for_raw_material_request:
					total_work_order_qty = flt(
						qb.from_(wo)
						.select(Sum(wo.qty))
						.where(
							(wo.production_item == i.item_code)
							& (wo.proforma == so.name)
							& (wo.proforma_item == i.name)
							& (wo.docstatus.lt(2))
						)
						.run()[0][0]
					)
					pending_qty = stock_qty - total_work_order_qty
				else:
					pending_qty = stock_qty

				if pending_qty and i.item_code not in product_bundle_parents:
					items.append(
						dict(
							name=i.name,
							item_code=i.item_code,
							description=i.description,
							bom=bom or "",
							warehouse=i.warehouse,
							pending_qty=pending_qty,
							required_qty=pending_qty if for_raw_material_request else 0,
							proforma_item=i.name,
						)
					)

		return items

@frappe.whitelist()
def get_stock_reservation_status():
	return frappe.db.get_single_value("Stock Settings", "enable_stock_reservation")