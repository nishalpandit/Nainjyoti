API for List All Categories
url: http://192.168.1.52:8000/api/categories/
method: GET

params:
none

response:
{
  "success": true,
  "count": 4,
  "categories": [
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "slug": "fashion-textiles",
      "description": "Ethnic wear, fabrics, apparel, handcrafted garments and modern fashion",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-shirt",
      "commission_rate": 10.0,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 2,
      "created_at": "2026-10-17T04:34:09.012458+00:00",
      "updated_at": "2026-10-17T04:34:09.012489+00:00"
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

API for List Root Categories Only
url: http://192.168.1.52:8000/api/categories/?parent=null
method: GET

params:
parent: null

response:
{
  "success": true,
  "count": 2,
  "categories": [
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "slug": "fashion-textiles",
      "description": "Ethnic wear, fabrics, apparel, handcrafted garments and modern fashion",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-shirt",
      "commission_rate": 10.0,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 2,
      "created_at": "2026-10-17T04:34:09.012458+00:00",
      "updated_at": "2026-10-17T04:34:09.012489+00:00"
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
    }
  ]
}

API for List Subcategories by Parent ID
url: http://192.168.1.52:8000/api/categories/?parent_id=1
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
url: http://192.168.1.52:8000/api/categories/tree/
method: GET

params:
none

response:
{
  "success": true,
  "count": 2,
  "tree": [
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "slug": "fashion-textiles",
      "description": "Ethnic wear, fabrics, apparel, handcrafted garments and modern fashion",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-shirt",
      "commission_rate": 10.0,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 2,
      "created_at": "2026-10-17T04:34:09.012458+00:00",
      "updated_at": "2026-10-17T04:34:09.012489+00:00",
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
    }
  ]
}

API for Create Category
url: http://192.168.1.52:8000/api/categories/
method: POST

params:
name: Fashion & Textiles
description: Ethnic wear, fabrics, apparel, handcrafted garments and modern fashion
commission_rate: 10.00
icon: fa-shirt
display_order: 1
is_active: true

response:
{
  "success": true,
  "message": "Category created successfully",
  "category": {
    "id": 1,
    "name": "Fashion & Textiles",
    "slug": "fashion-textiles",
    "description": "Ethnic wear, fabrics, apparel, handcrafted garments and modern fashion",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-shirt",
    "commission_rate": 10.0,
    "display_order": 1,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:34:09.012458+00:00",
    "updated_at": "2026-10-17T04:34:09.012489+00:00",
    "subcategories": []
  }
}

API for Create Subcategory
url: http://192.168.1.52:8000/api/categories/
method: POST

params:
name: Kashmiri Shawls & Stoles
description: Authentic hand-woven Pashmina, Cashmere and embroidered woollen shawls
parent_id: 1
commission_rate: 12.00
icon: fa-vest
display_order: 1
is_active: true

response:
{
  "success": true,
  "message": "Category created successfully",
  "category": {
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
    "updated_at": "2026-10-17T04:34:09.070967+00:00",
    "subcategories": []
  }
}

API for Get Category Details by ID
url: http://192.168.1.52:8000/api/categories/1/
method: GET

params:
none

response:
{
  "success": true,
  "category": {
    "id": 1,
    "name": "Fashion & Textiles",
    "slug": "fashion-textiles",
    "description": "Ethnic wear, fabrics, apparel, handcrafted garments and modern fashion",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-shirt",
    "commission_rate": 10.0,
    "display_order": 1,
    "is_active": true,
    "subcategories_count": 2,
    "created_at": "2026-10-17T04:34:09.012458+00:00",
    "updated_at": "2026-10-17T04:34:09.012489+00:00",
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
  }
}

API for Get Category Details by Slug
url: http://192.168.1.52:8000/api/categories/slug/fashion-textiles/
method: GET

params:
none

response:
{
  "success": true,
  "category": {
    "id": 1,
    "name": "Fashion & Textiles",
    "slug": "fashion-textiles",
    "description": "Ethnic wear, fabrics, apparel, handcrafted garments and modern fashion",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-shirt",
    "commission_rate": 10.0,
    "display_order": 1,
    "is_active": true,
    "subcategories_count": 2,
    "created_at": "2026-10-17T04:34:09.012458+00:00",
    "updated_at": "2026-10-17T04:34:09.012489+00:00",
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
  }
}

API for Update Category
url: http://192.168.1.52:8000/api/categories/1/
method: PUT

params:
commission_rate: 9.50
description: Updated: Premium ethnic wear, fabrics, apparel, Kashmiri shawls and modern fashion
icon: fa-shirt

response:
{
  "success": true,
  "message": "Category updated successfully",
  "category": {
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
    "updated_at": "2026-10-17T04:34:09.223131+00:00",
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
  }
}

API for Soft Delete Category
url: http://192.168.1.52:8000/api/categories/5/?soft=true
method: DELETE

params:
soft: true

response:
{
  "success": true,
  "message": "Category 'Temporary Sample Category' marked as inactive (soft deleted).",
  "category_id": 5,
  "is_active": false
}

API for Delete Category
url: http://192.168.1.52:8000/api/categories/5/
method: DELETE

params:
none

response:
{
  "success": true,
  "message": "Category 'Temporary Sample Category' (ID: 5) deleted successfully.",
  "category_id": 5
}
