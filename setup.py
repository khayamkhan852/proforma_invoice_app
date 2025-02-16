from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in proforma_invoice_app/__init__.py
from proforma_invoice_app import __version__ as version

setup(
	name="proforma_invoice_app",
	version=version,
	description="Custom Frappe ERPNext application for For Creating Proforma Invoice",
	author="Khayam Khan",
	author_email="khayamkhan852@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)