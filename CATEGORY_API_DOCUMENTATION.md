API for Create Category
url: http://192.168.1.52:8000/api/vendor/category/create/
method: POST

params:
name: Handmade Wooden Carvings
description: Authentic walnut wood and deodar handcrafted decorative art pieces
commission_rate: 8.00
icon: fa-tree
display_order: 3
is_active: true

response:
{
  "success": true,
  "message": "Category created successfully",
  "category": {
    "id": 7,
    "name": "Handmade Wooden Carvings",
    "slug": "handmade-wooden-carvings",
    "description": "Authentic walnut wood and deodar handcrafted decorative art pieces",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-tree",
    "commission_rate": 8.0,
    "display_order": 3,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:45:07.135766+00:00",
    "updated_at": "2026-10-17T04:45:07.135799+00:00",
    "subcategories": []
  }
}

API for Create Subcategory
url: http://192.168.1.52:8000/api/vendor/category/create/
method: POST

params:
name: Walnut Jewelry Boxes
description: Intricately carved Kashmiri walnut wood jewelry boxes with brass inlays
parent_id: 7
commission_rate: 9.50
icon: fa-gem
display_order: 1
is_active: true

response:
{
  "success": true,
  "message": "Category created successfully",
  "category": {
    "id": 8,
    "name": "Walnut Jewelry Boxes",
    "slug": "walnut-jewelry-boxes",
    "description": "Intricately carved Kashmiri walnut wood jewelry boxes with brass inlays",
    "parent_id": 7,
    "parent_name": "Handmade Wooden Carvings",
    "image": null,
    "icon": "fa-gem",
    "commission_rate": 9.5,
    "display_order": 1,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:45:07.165842+00:00",
    "updated_at": "2026-10-17T04:45:07.165866+00:00",
    "subcategories": []
  }
}

API for List All Categories
url: http://192.168.1.52:8000/api/vendor/category/list/
method: GET

params:
none

response:
{
  "success": true,
  "count": 5,
  "categories": [
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "slug": "fashion-textiles",
      "description": "Updated: Premium ethnic wear, fabrics, apparel, Kashmiri shawls and modern fashion",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-shirt",
      "commission_rate": 9.5,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 2,
      "created_at": "2026-10-17T04:34:09.012458+00:00",
      "updated_at": "2026-10-17T04:37:34.865589+00:00"
    },
    {
      "id": 3,
      "name": "Kashmiri Shawls & Stoles",
      "slug": "kashmiri-shawls-stoles",
      "description": "Authentic hand-woven Pashmina, Cashmere and embroidered woollen shawls",
      "parent_id": 1,
      "parent_name": "Fashion & Textiles",
      "image": null,
      "icon": "fa-vest",
      "commission_rate": 12.0,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.070945+00:00",
      "updated_at": "2026-10-17T04:34:09.070967+00:00"
    },
    {
      "id": 2,
      "name": "Electronics & Appliances",
      "slug": "electronics-appliances",
      "description": "Smartphones, home appliances, wearable devices and smart gadgets",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-laptop",
      "commission_rate": 7.5,
      "display_order": 2,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.041989+00:00",
      "updated_at": "2026-10-17T04:34:09.042016+00:00"
    },
    {
      "id": 4,
      "name": "Handcrafted Silk Sarees",
      "slug": "handcrafted-silk-sarees",
      "description": "Traditional banarasi, chanderi, and pure silk heritage sarees",
      "parent_id": 1,
      "parent_name": "Fashion & Textiles",
      "image": null,
      "icon": "fa-ribbon",
      "commission_rate": 10.0,
      "display_order": 2,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.100814+00:00",
      "updated_at": "2026-10-17T04:34:09.100835+00:00"
    },
    {
      "id": 7,
      "name": "Handmade Wooden Carvings",
      "slug": "handmade-wooden-carvings",
      "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-tree",
      "commission_rate": 7.5,
      "display_order": 3,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:45:07.135766+00:00",
      "updated_at": "2026-10-17T04:45:07.218529+00:00"
    }
  ]
}

API for List Root Categories Only
url: http://192.168.1.52:8000/api/vendor/category/list/?parent=null
method: GET

params:
parent: null

response:
{
  "success": true,
  "count": 3,
  "categories": [
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "slug": "fashion-textiles",
      "description": "Updated: Premium ethnic wear, fabrics, apparel, Kashmiri shawls and modern fashion",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-shirt",
      "commission_rate": 9.5,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 2,
      "created_at": "2026-10-17T04:34:09.012458+00:00",
      "updated_at": "2026-10-17T04:37:34.865589+00:00"
    },
    {
      "id": 2,
      "name": "Electronics & Appliances",
      "slug": "electronics-appliances",
      "description": "Smartphones, home appliances, wearable devices and smart gadgets",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-laptop",
      "commission_rate": 7.5,
      "display_order": 2,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.041989+00:00",
      "updated_at": "2026-10-17T04:34:09.042016+00:00"
    },
    {
      "id": 7,
      "name": "Handmade Wooden Carvings",
      "slug": "handmade-wooden-carvings",
      "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-tree",
      "commission_rate": 7.5,
      "display_order": 3,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:45:07.135766+00:00",
      "updated_at": "2026-10-17T04:45:07.218529+00:00"
    }
  ]
}

API for List Subcategories by Parent ID
url: http://192.168.1.52:8000/api/vendor/category/list/?parent_id=1
method: GET

params:
parent_id: 1

response:
{
  "success": true,
  "count": 2,
  "categories": [
    {
      "id": 3,
      "name": "Kashmiri Shawls & Stoles",
      "slug": "kashmiri-shawls-stoles",
      "description": "Authentic hand-woven Pashmina, Cashmere and embroidered woollen shawls",
      "parent_id": 1,
      "parent_name": "Fashion & Textiles",
      "image": null,
      "icon": "fa-vest",
      "commission_rate": 12.0,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.070945+00:00",
      "updated_at": "2026-10-17T04:34:09.070967+00:00"
    },
    {
      "id": 4,
      "name": "Handcrafted Silk Sarees",
      "slug": "handcrafted-silk-sarees",
      "description": "Traditional banarasi, chanderi, and pure silk heritage sarees",
      "parent_id": 1,
      "parent_name": "Fashion & Textiles",
      "image": null,
      "icon": "fa-ribbon",
      "commission_rate": 10.0,
      "display_order": 2,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.100814+00:00",
      "updated_at": "2026-10-17T04:34:09.100835+00:00"
    }
  ]
}

API for Category Hierarchy Tree
url: http://192.168.1.52:8000/api/vendor/category/tree/
method: GET

params:
none

response:
{
  "success": true,
  "count": 3,
  "tree": [
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "slug": "fashion-textiles",
      "description": "Updated: Premium ethnic wear, fabrics, apparel, Kashmiri shawls and modern fashion",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-shirt",
      "commission_rate": 9.5,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 2,
      "created_at": "2026-10-17T04:34:09.012458+00:00",
      "updated_at": "2026-10-17T04:37:34.865589+00:00",
      "subcategories": [
        {
          "id": 3,
          "name": "Kashmiri Shawls & Stoles",
          "slug": "kashmiri-shawls-stoles",
          "description": "Authentic hand-woven Pashmina, Cashmere and embroidered woollen shawls",
          "parent_id": 1,
          "parent_name": "Fashion & Textiles",
          "image": null,
          "icon": "fa-vest",
          "commission_rate": 12.0,
          "display_order": 1,
          "is_active": true,
          "subcategories_count": 0,
          "created_at": "2026-10-17T04:34:09.070945+00:00",
          "updated_at": "2026-10-17T04:34:09.070967+00:00"
        },
        {
          "id": 4,
          "name": "Handcrafted Silk Sarees",
          "slug": "handcrafted-silk-sarees",
          "description": "Traditional banarasi, chanderi, and pure silk heritage sarees",
          "parent_id": 1,
          "parent_name": "Fashion & Textiles",
          "image": null,
          "icon": "fa-ribbon",
          "commission_rate": 10.0,
          "display_order": 2,
          "is_active": true,
          "subcategories_count": 0,
          "created_at": "2026-10-17T04:34:09.100814+00:00",
          "updated_at": "2026-10-17T04:34:09.100835+00:00"
        }
      ]
    },
    {
      "id": 2,
      "name": "Electronics & Appliances",
      "slug": "electronics-appliances",
      "description": "Smartphones, home appliances, wearable devices and smart gadgets",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-laptop",
      "commission_rate": 7.5,
      "display_order": 2,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.041989+00:00",
      "updated_at": "2026-10-17T04:34:09.042016+00:00",
      "subcategories": []
    },
    {
      "id": 7,
      "name": "Handmade Wooden Carvings",
      "slug": "handmade-wooden-carvings",
      "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-tree",
      "commission_rate": 7.5,
      "display_order": 3,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:45:07.135766+00:00",
      "updated_at": "2026-10-17T04:45:07.218529+00:00",
      "subcategories": []
    }
  ]
}

API for Get Category Details
url: http://192.168.1.52:8000/api/vendor/category/detail/7/
method: GET

params:
none

response:
{
  "success": true,
  "category": {
    "id": 7,
    "name": "Handmade Wooden Carvings",
    "slug": "handmade-wooden-carvings",
    "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-tree",
    "commission_rate": 7.5,
    "display_order": 3,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:45:07.135766+00:00",
    "updated_at": "2026-10-17T04:45:07.218529+00:00",
    "subcategories": []
  }
}

API for Update Category
url: http://192.168.1.52:8000/api/vendor/category/update/7/
method: POST

params:
commission_rate: 7.50
description: Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art
icon: fa-tree

response:
{
  "success": true,
  "message": "Category updated successfully",
  "category": {
    "id": 7,
    "name": "Handmade Wooden Carvings",
    "slug": "handmade-wooden-carvings",
    "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-tree",
    "commission_rate": 7.5,
    "display_order": 3,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:45:07.135766+00:00",
    "updated_at": "2026-10-17T04:45:07.218529+00:00"
  }
}

API for Soft Delete Category
url: http://192.168.1.52:8000/api/vendor/category/delete/8/?soft=true
method: POST

params:
soft: true

response:
{
  "success": true,
  "message": "Category 'Walnut Jewelry Boxes' marked as inactive (soft deleted).",
  "category_id": 8,
  "is_active": false
}

API for Delete Category
url: http://192.168.1.52:8000/api/vendor/category/delete/8/
method: POST

params:
none

response:
{
  "success": true,
  "message": "Category 'Walnut Jewelry Boxes' (ID: 8) deleted successfully.",
  "category_id": 8
}
