API for Create Category
url: http://192.168.1.52:8000/api/vendor/category/create/
method: POST

params:
name: Handicrafts & Handlooms
status: ACTIVE

response:
{
  "success": true,
  "message": "Category created successfully",
  "category": {
    "id": 8,
    "name": "Handicrafts & Handlooms",
    "status": "ACTIVE"
  }
}

API for List Categories
url: http://192.168.1.52:8000/api/vendor/category/list/
method: GET

params:
status: ACTIVE (optional, filter by ACTIVE or INACTIVE)
search: Handicrafts (optional, search by name)

response:
{
  "success": true,
  "count": 5,
  "categories": [
    {
      "id": 8,
      "name": "Handicrafts & Handlooms",
      "status": "ACTIVE"
    },
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "status": "ACTIVE"
    },
    {
      "id": 2,
      "name": "Electronics & Appliances",
      "status": "ACTIVE"
    },
    {
      "id": 4,
      "name": "Handcrafted Silk Sarees",
      "status": "ACTIVE"
    },
    {
      "id": 7,
      "name": "Handmade Wooden Carvings",
      "status": "ACTIVE"
    }
  ]
}

API for Get Category Details
url: http://192.168.1.52:8000/api/vendor/category/detail/8/
method: GET

params:
none

response:
{
  "success": true,
  "category": {
    "id": 8,
    "name": "Handicrafts & Handlooms",
    "status": "ACTIVE"
  }
}

API for Update Category
url: http://192.168.1.52:8000/api/vendor/category/update/8/
method: POST

params:
name: Handicrafts & Handlooms
status: INACTIVE

response:
{
  "success": true,
  "message": "Category updated successfully",
  "category": {
    "id": 8,
    "name": "Handicrafts & Handlooms",
    "status": "INACTIVE"
  }
}

API for Delete Category
url: http://192.168.1.52:8000/api/vendor/category/delete/8/
method: POST

params:
none

response:
{
  "success": true,
  "message": "Category 'Handicrafts & Handlooms' (ID: 8) deleted successfully.",
  "category_id": 8
}
