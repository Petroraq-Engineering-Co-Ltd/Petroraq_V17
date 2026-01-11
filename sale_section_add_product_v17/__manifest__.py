{
    "name": "Sale Section Add Product (v17)",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "summary": "Add products directly under each section in sale order",
    "depends": ["sale", "account"],
    "assets": {
        "web.assets_backend": [
            "sale_section_add_product_v17/static/src/xml/section_add_product.xml",
            "sale_section_add_product_v17/static/src/js/section_add_product.js",
            "sale_section_add_product_v17/static/src/css/section_add_product.css",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
