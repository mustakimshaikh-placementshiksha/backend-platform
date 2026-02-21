# 🎨 UI Developer API Guide — OnlineJudge Backend

> **For:** Frontend / UI Developers  
> **Backend Base URL:** `http://localhost:8000` (dev) — replace with production URL when deployed  
> **Interactive Docs:** http://localhost:8000/swagger/  
> **ReDoc (clean readable docs):** http://localhost:8000/redoc/  
> **All API responses follow the same envelope format (see below)**

---

## 📋 Table of Contents

1. [Standard Response Format](#1-standard-response-format)
2. [Authentication — Login & Session](#2-authentication--login--session)
3. [Problem Upload — Single Problem (Step by Step)](#3-problem-upload--single-problem-step-by-step)
4. [Problem Upload — Batch via ZIP (Many Problems at Once)](#4-problem-upload--batch-via-zip-many-problems-at-once)
5. [Problem Upload — Batch via FPS XML (Many Problems at Once)](#5-problem-upload--batch-via-fps-xml-many-problems-at-once)
6. [Problem Management (List, Edit, Delete)](#6-problem-management-list-edit-delete)
7. [Export Problems](#7-export-problems)
8. [Full Field Reference — Problem Fields Explained](#8-full-field-reference--problem-fields-explained)
9. [Test Case ZIP Format — Detailed](#9-test-case-zip-format--detailed)
10. [FPS XML Format — Detailed](#10-fps-xml-format--detailed)
11. [All API Endpoints Quick Reference](#11-all-api-endpoints-quick-reference)
12. [Common Errors & What They Mean](#12-common-errors--what-they-mean)

---

## 1. Standard Response Format

**Every single API response** from this backend uses this wrapper:

```json
{
  "error": null,
  "data": { ... }
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `error` | `null` or `"string"` | `null` = success. A string = error message to show user |
| `data` | any | The actual payload (object, list, number, etc.) |

**Paginated list responses** look like this:

```json
{
  "error": null,
  "data": {
    "total": 42,
    "results": [ {...}, {...}, {...} ]
  }
}
```

> ✅ **UI Rule:** Always check `error !== null` first. If it's a string, show it as an error toast/message.

---

## 2. Authentication — Login & Session

All admin-level endpoints (problem creation, problem management, etc.) require the user to be **logged in as Admin or Super Admin**.

### 2.1 — Login

**`POST /api/account/login/`**

#### Request Body (JSON):
```json
{
  "username": "root",
  "password": "rootroot"
}
```

#### Success Response:
```json
{
  "error": null,
  "data": {
    "id": 1,
    "username": "root",
    "admin_type": "Super Admin",
    "problem_permission": "All",
    "two_factor_auth": false,
    "open_api": false,
    "is_disabled": false
  }
}
```

#### What the UI must do after login:
- The backend **automatically sets a `sessionid` cookie** in the browser
- All subsequent API calls **must include this cookie** (use `credentials: "include"` in `fetch`)
- Store the `admin_type` to conditionally show/hide admin features

#### JavaScript Fetch Example:
```javascript
const response = await fetch('http://localhost:8000/api/account/login/', {
  method: 'POST',
  credentials: 'include',          // ← REQUIRED for session cookie
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'root', password: 'rootroot' })
});
const json = await response.json();
if (json.error) {
  alert('Login failed: ' + json.error);
} else {
  // logged in! json.data has user info
}
```

---

### 2.2 — Logout

**`POST /api/account/logout/`**

```javascript
await fetch('http://localhost:8000/api/account/logout/', {
  method: 'POST',
  credentials: 'include'
});
```

---

### 2.3 — Get Current User Profile

**`GET /api/account/profile/`**

Returns the logged-in user's profile. Use this to check if someone is already logged in when the page loads.

```json
{
  "error": null,
  "data": {
    "id": 1,
    "user": {
      "id": 1,
      "username": "root",
      "admin_type": "Super Admin",
      "problem_permission": "All"
    },
    "real_name": null,
    "avatar": "/public/avatar/default.png",
    "accepted_number": 0,
    "submission_number": 0
  }
}
```

---

### 2.4 — CSRF Token (Required for POST/PUT/DELETE)

Django requires a **CSRF token** on all mutating requests.

#### How to get it:
The CSRF token is automatically stored in a cookie called `csrftoken` after you visit any page (or make any GET request).

#### How to send it:
Always include the `X-CSRFToken` header:

```javascript
// Helper — reads CSRF token from cookie
function getCsrfToken() {
  return document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
}

// Example POST with CSRF
const resp = await fetch('http://localhost:8000/api/problem/admin/problem/', {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken()   // ← REQUIRED
  },
  body: JSON.stringify({ /* problem data */ })
});
```

---

## 3. Problem Upload — Single Problem (Step by Step)

Adding a single problem requires **2 API calls**:
1. **Upload test cases** → get a `test_case_id`
2. **Create the problem** → use the `test_case_id`

---

### STEP 1 — Upload Test Cases

**`POST /api/problem/admin/test_case/`**  
`Content-Type: multipart/form-data`

#### What you upload:
A `.zip` file containing numbered input/output pairs:
```
testcases.zip
├── 1.in      ← input for test case 1
├── 1.out     ← expected output for test case 1
├── 2.in      ← input for test case 2
├── 2.out     ← expected output for test case 2
└── 3.in / 3.out ...   (as many as you want)
```

#### Form Fields:
| Field | Type | Required | Value |
|-------|------|----------|-------|
| `file` | File | ✅ Yes | The `.zip` file |
| `spj` | String | ✅ Yes | `"false"` for normal, `"true"` for Special Judge |

#### Success Response:
```json
{
  "error": null,
  "data": {
    "id": "a3f8c2d1e9b047f6ad12345678abcdef",
    "spj": false,
    "info": [
      {
        "input_name": "1.in",
        "output_name": "1.out",
        "input_size": 4,
        "output_size": 2,
        "stripped_output_md5": "abc123..."
      },
      {
        "input_name": "2.in",
        "output_name": "2.out",
        "input_size": 6,
        "output_size": 3,
        "stripped_output_md5": "def456..."
      }
    ]
  }
}
```

> 🔑 **Save the `data.id` — this is your `test_case_id` for the next step!**

#### JavaScript Example:
```javascript
async function uploadTestCases(zipFile) {
  const formData = new FormData();
  formData.append('file', zipFile);     // File object from <input type="file">
  formData.append('spj', 'false');      // 'false' for regular problems

  const resp = await fetch('http://localhost:8000/api/problem/admin/test_case/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: formData                        // No Content-Type header! Browser sets it
  });
  const json = await resp.json();
  if (json.error) throw new Error(json.error);
  return json.data.id;   // ← test_case_id to use in Step 2
}
```

---

### STEP 2 — Create the Problem

**`POST /api/problem/admin/problem/`**  
`Content-Type: application/json`

#### Full Request Body:
```json
{
  "_id": "1001",
  "title": "A + B Problem",
  "description": "<p>You are given two integers A and B. Output their sum.</p>",
  "input_description": "<p>A single line containing two integers A and B separated by a space.</p>",
  "output_description": "<p>Output a single integer: A + B.</p>",
  "hint": "<p>Both A and B are between 0 and 1000.</p>",
  "source": "Classic Problem",
  "samples": [
    { "input": "1 2", "output": "3" },
    { "input": "100 200", "output": "300" }
  ],
  "test_case_id": "a3f8c2d1e9b047f6ad12345678abcdef",
  "test_case_score": [],
  "time_limit": 1000,
  "memory_limit": 256,
  "difficulty": "Low",
  "visible": true,
  "tags": ["math", "beginner"],
  "languages": ["C", "C++", "Java", "Python3"],
  "template": {},
  "rule_type": "ACM",
  "io_mode": {
    "io_mode": "Standard IO",
    "input": "input.txt",
    "output": "output.txt"
  },
  "spj": false,
  "spj_language": null,
  "spj_code": null,
  "spj_compile_ok": false,
  "share_submission": false
}
```

#### Success Response:
```json
{
  "error": null,
  "data": {
    "id": 5,
    "_id": "1001",
    "title": "A + B Problem",
    "difficulty": "Low",
    "visible": true,
    "tags": ["math", "beginner"],
    "create_time": "2026-02-21T07:00:00.000Z",
    ...
  }
}
```

#### JavaScript Example (Full Single Problem Upload):
```javascript
async function createSingleProblem(zipFile, problemData) {
  // Step 1: Upload test cases
  const testCaseId = await uploadTestCases(zipFile);
  
  // Step 2: Create problem with the test_case_id
  const body = {
    _id: problemData.displayId,
    title: problemData.title,
    description: problemData.description,
    input_description: problemData.inputDesc,
    output_description: problemData.outputDesc,
    hint: problemData.hint || '',
    source: problemData.source || '',
    samples: problemData.samples,
    test_case_id: testCaseId,        // ← from step 1
    test_case_score: [],
    time_limit: problemData.timeLimit || 1000,
    memory_limit: problemData.memoryLimit || 256,
    difficulty: problemData.difficulty || 'Mid',
    visible: true,
    tags: problemData.tags || [],
    languages: ['C', 'C++', 'Java', 'Python3'],
    template: {},
    rule_type: 'ACM',
    io_mode: { io_mode: 'Standard IO', input: 'input.txt', output: 'output.txt' },
    spj: false,
    spj_language: null,
    spj_code: null,
    spj_compile_ok: false,
    share_submission: false
  };

  const resp = await fetch('http://localhost:8000/api/problem/admin/problem/', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(body)
  });
  const json = await resp.json();
  if (json.error) throw new Error(json.error);
  return json.data;   // created problem object
}
```

---

## 4. Problem Upload — Batch via ZIP (Many Problems at Once)

Use this when you want to **upload 10, 50, 100+ problems at the same time** from a single ZIP file.

**`POST /api/problem/admin/import_problem/`**  
`Content-Type: multipart/form-data`

---

### ZIP File Structure (Strict — must follow exactly):

```
batch_problems.zip
│
├── 1/                         ← Problem 1
│   ├── problem.json           ← Problem metadata (required)
│   └── testcase/              ← Test cases folder (required)
│       ├── 1.in
│       ├── 1.out
│       ├── 2.in
│       └── 2.out
│
├── 2/                         ← Problem 2
│   ├── problem.json
│   └── testcase/
│       ├── 1.in
│       ├── 1.out
│       └── 2.in / 2.out
│
├── 3/                         ← Problem 3
│   ├── problem.json
│   └── testcase/
│       └── 1.in / 1.out
│
└── 4/ ... 5/ ... 6/ ... (as many as you want)
```

> ✅ **Folders MUST be numbered `1`, `2`, `3` ... sequentially. No gaps.**

---

### `problem.json` Format (inside each folder):

```json
{
  "display_id": "1001",
  "title": "A + B Problem",
  "description": {
    "format": "html",
    "value": "<p>Given two integers A and B, output their sum.</p>"
  },
  "input_description": {
    "format": "html",
    "value": "<p>Two integers A and B on a single line.</p>"
  },
  "output_description": {
    "format": "html",
    "value": "<p>Output A + B.</p>"
  },
  "hint": {
    "format": "html",
    "value": "<p>Both values are between 0 and 1000.</p>"
  },
  "time_limit": 1000,
  "memory_limit": 256,
  "samples": [
    { "input": "1 2", "output": "3" },
    { "input": "0 0", "output": "0" }
  ],
  "test_case_score": [
    { "score": 50, "input_name": "1.in", "output_name": "1.out" },
    { "score": 50, "input_name": "2.in", "output_name": "2.out" }
  ],
  "rule_type": "ACM",
  "source": "Classic",
  "tags": ["math", "easy"],
  "template": {},
  "spj": null,
  "answers": []
}
```

#### `problem.json` Field Reference:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `display_id` | string | ✅ | Must be unique across all problems (max 24 chars) |
| `title` | string | ✅ | Problem title |
| `description` | `{format, value}` | ✅ | HTML content of the problem |
| `input_description` | `{format, value}` | ✅ | Input format description |
| `output_description` | `{format, value}` | ✅ | Output format description |
| `hint` | `{format, value}` | ✅ | Hints (can be empty string in value) |
| `time_limit` | int (ms) | ✅ | e.g. `1000` = 1 second |
| `memory_limit` | int (MB) | ✅ | e.g. `256` = 256 MB |
| `samples` | array | ✅ | `[{ "input": "...", "output": "..." }]` |
| `test_case_score` | array | ✅ | Score per test case (use `0` for ACM mode) |
| `rule_type` | string | ✅ | `"ACM"` or `"OI"` |
| `source` | string | ❌ | Where the problem is from |
| `tags` | array of strings | ✅ | e.g. `["math", "dp"]` |
| `template` | object | ✅ | Code templates per language (can be `{}`) |
| `spj` | null or object | ✅ | `null` for normal, `{"code":"...","language":"C"}` for Special Judge |
| `answers` | array | ❌ | Sample solutions (optional) |

---

### Upload the ZIP via UI:

```javascript
async function uploadBatchProblems(zipFile) {
  const formData = new FormData();
  formData.append('file', zipFile);

  const resp = await fetch('http://localhost:8000/api/problem/admin/import_problem/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: formData
  });
  const json = await resp.json();
  if (json.error) throw new Error(json.error);
  
  console.log(`✅ Imported ${json.data.import_count} problems!`);
  return json.data.import_count;
}
```

#### Success Response:
```json
{
  "error": null,
  "data": {
    "import_count": 25
  }
}
```

> 🔥 **This single API call can import unlimited problems.** Just add more numbered folders to the ZIP.

---

### How to generate this ZIP automatically (easiest way):

Use the **Export endpoint** on existing problems. It generates a perfectly structured ZIP:

```
GET /api/problem/admin/export_problem/?problem_id=1&problem_id=2&problem_id=3
```

Download the ZIP → modify the `problem.json` files → re-upload to import.

---

## 5. Problem Upload — Batch via FPS XML (Many Problems at Once)

Use this format if you're importing from **HUSTOJ, OnlineJudge systems, or any system that supports the FPS (FreeProblemSet) XML format**.

**`POST /api/problem/admin/import_fps/`**  
`Content-Type: multipart/form-data`

---

### FPS XML File Format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<fps version="1.2" url="https://github.com/zhblue/freeproblemset/">
  <generator name="MySystem" url="https://example.com"/>

  <!-- ============ PROBLEM 1 ============ -->
  <item>
    <title><![CDATA[A + B Problem]]></title>
    <time_limit unit="s"><![CDATA[1]]></time_limit>
    <memory_limit unit="mb"><![CDATA[256]]></memory_limit>
    <description><![CDATA[<p>Given integers A and B, output A+B.</p>]]></description>
    <input><![CDATA[<p>Two integers A B on one line.</p>]]></input>
    <output><![CDATA[<p>Output A+B.</p>]]></output>
    <hint><![CDATA[<p>0 ≤ A, B ≤ 1000</p>]]></hint>
    <source><![CDATA[Classic]]></source>

    <!-- Sample test cases (shown to users) -->
    <sample_input><![CDATA[1 2]]></sample_input>
    <sample_output><![CDATA[3]]></sample_output>

    <!-- Actual test cases (hidden, used for judging) -->
    <test_input><![CDATA[5 7]]></test_input>
    <test_output><![CDATA[12]]></test_output>
    <test_input><![CDATA[100 200]]></test_input>
    <test_output><![CDATA[300]]></test_output>
    <test_input><![CDATA[0 0]]></test_input>
    <test_output><![CDATA[0]]></test_output>

    <!-- Code templates (optional) -->
    <template language="C++"><![CDATA[#include<iostream>
using namespace std;
int main(){
    int a, b;
    cin >> a >> b;
    cout << a+b << endl;
}]]></template>
  </item>

  <!-- ============ PROBLEM 2 ============ -->
  <item>
    <title><![CDATA[Fibonacci Number]]></title>
    <time_limit unit="s"><![CDATA[2]]></time_limit>
    <memory_limit unit="mb"><![CDATA[128]]></memory_limit>
    <description><![CDATA[<p>Find the Nth Fibonacci number.</p>]]></description>
    <input><![CDATA[<p>An integer N (1 ≤ N ≤ 30)</p>]]></input>
    <output><![CDATA[<p>Output the Nth Fibonacci number.</p>]]></output>
    <hint><![CDATA[]]></hint>
    <source><![CDATA[Math]]></source>
    <sample_input><![CDATA[5]]></sample_input>
    <sample_output><![CDATA[5]]></sample_output>
    <test_input><![CDATA[1]]></test_input>
    <test_output><![CDATA[1]]></test_output>
    <test_input><![CDATA[10]]></test_input>
    <test_output><![CDATA[55]]></test_output>
  </item>

  <!-- Add as many <item> blocks as needed -->

</fps>
```

### FPS XML Tag Reference:

| XML Tag | Required | Notes |
|---------|----------|-------|
| `<title>` | ✅ | Problem title |
| `<time_limit unit="s">` or `unit="ms"` | ✅ | Time limit (supports seconds or ms) |
| `<memory_limit unit="mb">` | ✅ | Memory limit in MB |
| `<description>` | ✅ | HTML problem description |
| `<input>` | ✅ | HTML input format |
| `<output>` | ✅ | HTML output format |
| `<hint>` | ❌ | HTML hints |
| `<source>` | ❌ | Source/origin of problem |
| `<sample_input>` + `<sample_output>` | ✅ | Paired — shown to users |
| `<test_input>` + `<test_output>` | ✅ | Paired — used for judging (add as many as you want) |
| `<template language="...">` | ❌ | Code templates per language |
| `<solution language="...">` | ❌ | Reference solutions |
| `<spj language="C">` | ❌ | Special Judge code |

### Upload via UI:

```javascript
async function uploadFPSProblems(xmlFile) {
  const formData = new FormData();
  formData.append('file', xmlFile);    // .xml file

  const resp = await fetch('http://localhost:8000/api/problem/admin/import_fps/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: formData
  });
  const json = await resp.json();
  if (json.error) throw new Error(json.error);

  console.log(`✅ Imported ${json.data.import_count} problems from FPS!`);
  return json.data.import_count;
}
```

#### Success Response:
```json
{
  "error": null,
  "data": {
    "import_count": 10
  }
}
```

> ✅ **The FPS file can contain unlimited `<item>` blocks.** All are imported in one request.  
> ⚠️ FPS-imported problems get auto-generated display IDs like `fps-a3f2`, not sequential numbers.  
> ⚠️ FPS-imported problems are set to **visible = false** by default. You need to manually make them visible.

---

## 6. Problem Management (List, Edit, Delete)

### 6.1 — Get All Problems (Admin View)

**`GET /api/problem/admin/problem/`**

#### Query Parameters:
| Param | Type | Description |
|-------|------|-------------|
| `limit` | int | How many results per page (default: 10) |
| `offset` | int | Pagination offset (skip N records) |
| `keyword` | string | Search by title or display_id |
| `rule_type` | string | Filter by `"ACM"` or `"OI"` |
| `id` | int | Get a single problem by its DB id |

#### Example:
```
GET /api/problem/admin/problem/?limit=20&offset=0&keyword=fibonacci
```

#### Response:
```json
{
  "error": null,
  "data": {
    "total": 45,
    "results": [
      {
        "id": 1,
        "_id": "1001",
        "title": "A + B Problem",
        "difficulty": "Low",
        "visible": true,
        "tags": ["math"],
        "submission_number": 100,
        "accepted_number": 80,
        "create_time": "2026-02-21T07:00:00Z"
      },
      ...
    ]
  }
}
```

#### JavaScript Example:
```javascript
async function getProblems(page = 1, pageSize = 20, keyword = '') {
  const offset = (page - 1) * pageSize;
  const url = new URL('http://localhost:8000/api/problem/admin/problem/');
  url.searchParams.set('limit', pageSize);
  url.searchParams.set('offset', offset);
  if (keyword) url.searchParams.set('keyword', keyword);

  const resp = await fetch(url, { credentials: 'include' });
  const json = await resp.json();
  if (json.error) throw new Error(json.error);
  return json.data;   // { total, results }
}
```

---

### 6.2 — Edit a Problem

**`PUT /api/problem/admin/problem/`**  
`Content-Type: application/json`

Same body as Create (see Section 3, Step 2), but **add the `id` field** (the DB id from the GET response):

```json
{
  "id": 5,
  "_id": "1001",
  "title": "Updated Title",
  ...all other fields same as create...
}
```

---

### 6.3 — Delete a Problem

**`DELETE /api/problem/admin/problem/?id=5`**

```javascript
async function deleteProblem(problemId) {
  const resp = await fetch(
    `http://localhost:8000/api/problem/admin/problem/?id=${problemId}`,
    {
      method: 'DELETE',
      credentials: 'include',
      headers: { 'X-CSRFToken': getCsrfToken() }
    }
  );
  const json = await resp.json();
  if (json.error) throw new Error(json.error);
  return true;
}
```

---

### 6.4 — Toggle Problem Visibility

Use the **Edit endpoint** (`PUT`) and change `"visible": true` or `"visible": false`.

---

### 6.5 — Public Problem List (For Users / Non-Admin)

**`GET /api/problem/problem/`**

This is the public endpoint users see. Returns only visible problems. Filter parameters:

| Param | Description |
|-------|-------------|
| `limit` | Page size |
| `offset` | Pagination |
| `keyword` | Search |
| `difficulty` | `Low`, `Mid`, `High` |
| `tag` | Tag name |
| `rule_type` | `ACM` or `OI` |

---

## 7. Export Problems

**`GET /api/problem/admin/export_problem/`**

Export one or many problems as a ZIP file. The ZIP can be re-imported with the Import endpoint.

```
GET /api/problem/admin/export_problem/?problem_id=1&problem_id=2&problem_id=5
```

Returns a downloadable `problem-export.zip` file.

#### JavaScript Download:
```javascript
async function exportProblems(problemIds) {
  const params = problemIds.map(id => `problem_id=${id}`).join('&');
  const resp = await fetch(
    `http://localhost:8000/api/problem/admin/export_problem/?${params}`,
    { credentials: 'include' }
  );
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'problems-export.zip';
  a.click();
}
```

---

## 8. Full Field Reference — Problem Fields Explained

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | string (max 32) | ✅ | **Display ID** shown in URL. e.g. `"1001"`, `"A1"`. Must be unique. |
| `title` | string (max 1024) | ✅ | Problem title |
| `description` | HTML string | ✅ | Full problem description. HTML tags supported. |
| `input_description` | HTML string | ✅ | Describes the input format |
| `output_description` | HTML string | ✅ | Describes the expected output format |
| `hint` | HTML string | ❌ | Optional hints/notes. Can be empty (`""`) |
| `source` | string (max 256) | ❌ | Where the problem is from (e.g. `"Codeforces Round 100"`) |
| `samples` | array | ✅ | Visible examples: `[{ "input": "1 2", "output": "3" }]` (min 1 sample) |
| `test_case_id` | string | ✅ | ID returned from test case upload |
| `test_case_score` | array | ✅ | For OI mode: score per test case. For ACM: send `[]` |
| `time_limit` | int (ms) | ✅ | Milliseconds. e.g. `1000` = 1s, `2000` = 2s. Range: 1–60000 |
| `memory_limit` | int (MB) | ✅ | Megabytes. e.g. `256`. Range: 1–1024 |
| `difficulty` | string | ✅ | One of: `"Low"`, `"Mid"`, `"High"` |
| `visible` | boolean | ✅ | `true` = shown to regular users, `false` = hidden (draft) |
| `share_submission` | boolean | ✅ | Allow users to share their accepted code. Use `false` |
| `tags` | array of strings | ✅ | e.g. `["math", "greedy", "dp"]`. At least 1 required. |
| `languages` | array of strings | ✅ | Allowed languages. e.g. `["C", "C++", "Java", "Python3"]` |
| `template` | object | ✅ | Starter code per language. Use `{}` for none. |
| `rule_type` | string | ✅ | `"ACM"` (pass/fail per problem) or `"OI"` (partial scoring) |
| `io_mode` | object | ✅ | Always use `{ "io_mode": "Standard IO", "input": "input.txt", "output": "output.txt" }` |
| `spj` | boolean | ✅ | `false` for normal grading, `true` for Special Judge |
| `spj_language` | string or null | ✅ | Only if `spj: true`. e.g. `"C"` |
| `spj_code` | string or null | ✅ | SPJ source code. `null` for normal problems |
| `spj_compile_ok` | boolean | ✅ | `false` unless you've compiled and verified the SPJ code |

### Allowed values for `languages`:
```json
["C", "C++", "Python3", "Java", "JavaScript", "PyPy3", "Go", "Rust"]
```

### Allowed values for `rule_type`:
| Value | Meaning |
|-------|---------|
| `"ACM"` | All-or-nothing scoring. Accepted = full points. Wrong = 0. |
| `"OI"` | Partial scoring based on how many test cases pass. Each has a score. |

---

## 9. Test Case ZIP Format — Detailed

### Standard (non-SPJ) Problems:

Files must be named `1.in`, `1.out`, `2.in`, `2.out`, etc.:

```
testcases.zip
├── 1.in     ← input for test 1
├── 1.out    ← expected output for test 1
├── 2.in
├── 2.out
├── 3.in
└── 3.out
```

- Files must start from `1` — no `0.in` or `a.in`
- Must be paired — every `.in` must have a matching `.out`
- Line endings are normalized automatically (Windows `\r\n` → `\n`)
- No maximum limit on number of test cases

### OI Mode — `test_case_score` Format:

When `rule_type = "OI"`, each test case has a score. Use this format in the problem body:

```json
"test_case_score": [
  { "input_name": "1.in", "output_name": "1.out", "score": 30 },
  { "input_name": "2.in", "output_name": "2.out", "score": 30 },
  { "input_name": "3.in", "output_name": "3.out", "score": 40 }
]
```

> Total scores must add up to 100 for OI mode. For ACM use `[]`.

---

## 10. FPS XML Format — Detailed

### Supported FPS Versions: `1.1` and `1.2`

### Time Limit Units:
```xml
<time_limit unit="s">1</time_limit>     <!-- 1 second -->
<time_limit unit="ms">1500</time_limit>  <!-- 1500 milliseconds -->
```

### Memory Limit Units:
```xml
<memory_limit unit="mb">256</memory_limit>
<memory_limit unit="MB">256</memory_limit>
```

### Multiple Test Cases — Just Repeat the Tags:
```xml
<test_input><![CDATA[input for test 1]]></test_input>
<test_output><![CDATA[output for test 1]]></test_output>

<test_input><![CDATA[input for test 2]]></test_input>
<test_output><![CDATA[output for test 2]]></test_output>

<!-- as many as you want -->
```

### Multiple Languages in One Problem:
```xml
<template language="C++"><![CDATA[// your C++ starter code]]></template>
<template language="Java"><![CDATA[// your Java starter code]]></template>
<template language="Python"><![CDATA[# your Python starter code]]></template>
```

### Multiple Problems in One File — Just Repeat `<item>`:
```xml
<fps version="1.2">
  <item><!-- problem 1 --></item>
  <item><!-- problem 2 --></item>
  <item><!-- problem 3 --></item>
  <!-- ...100 problems if you want... -->
</fps>
```

---

## 11. All API Endpoints Quick Reference

### 🔐 Auth Endpoints

| Method | URL | Description | Auth Required |
|--------|-----|-------------|---------------|
| `POST` | `/api/account/login/` | Login | ❌ |
| `POST` | `/api/account/logout/` | Logout | ✅ |
| `POST` | `/api/account/register/` | Register new user | ❌ |
| `GET` | `/api/account/profile/` | Get current user profile | ✅ |
| `PUT` | `/api/account/profile/` | Update user profile | ✅ |
| `POST` | `/api/account/change_password/` | Change password | ✅ |
| `GET`/`POST` | `/api/account/two_factor_auth/` | 2FA management | ✅ |

### 🧩 Problem Endpoints (Admin)

| Method | URL | Description | Auth Required |
|--------|-----|-------------|---------------|
| `POST` | `/api/problem/admin/test_case/` | Upload test case ZIP | ✅ Admin |
| `GET` | `/api/problem/admin/test_case/?problem_id=N` | Download test case ZIP | ✅ Admin |
| `POST` | `/api/problem/admin/problem/` | Create one problem | ✅ Admin |
| `GET` | `/api/problem/admin/problem/` | List all problems | ✅ Admin |
| `PUT` | `/api/problem/admin/problem/` | Edit a problem | ✅ Admin |
| `DELETE` | `/api/problem/admin/problem/?id=N` | Delete a problem | ✅ Admin |
| `GET` | `/api/problem/admin/export_problem/` | Export problems as ZIP | ✅ Admin |
| `POST` | `/api/problem/admin/import_problem/` | Import from ZIP (batch) | ✅ Admin |
| `POST` | `/api/problem/admin/import_fps/` | Import from FPS XML (batch) | ✅ Admin |

### 🧩 Problem Endpoints (Public — Users)

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/problem/problem/` | List visible problems (paginated) |
| `GET` | `/api/problem/problem/?problem_id=1001` | Get single problem |
| `GET` | `/api/problem/problem/tags/` | Get all tags |
| `GET` | `/api/problem/pickone/` | Get a random problem |

### 🏅 Contest Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/contest/contest/` | List contests |
| `POST` | `/api/contest/admin/contest/` | Create contest (admin) |
| `POST` | `/api/problem/admin/contest/problem/` | Create contest problem |

### 📢 Announcements

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/announcement/announcement/` | Get all announcements |
| `POST` | `/api/announcement/admin/announcement/` | Create announcement (admin) |

---

## 12. Common Errors & What They Mean

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `"Login Please"` | Not logged in | Login first and include cookie |
| `"Permission Denied"` | User is not Admin | Login with an Admin account |
| `"Display ID already exists"` | `_id` already used by another problem | Use a different Display ID |
| `"Upload failed"` | File not attached properly | Check formData.append('file', ...) |
| `"Bad zip file"` | ZIP is corrupted | Re-create the ZIP file |
| `"Empty file"` | ZIP has no valid test cases | Check file naming (1.in, 1.out...) |
| `"Invalid problem format"` | `problem.json` has missing/wrong fields | Check all required fields |
| `"Test case does not exists"` | `test_case_id` is wrong | Re-upload test cases |
| `"Invalid spj"` | SPJ enabled but code is missing | Add `spj_code` and `spj_language` |
| `"Unsupported language"` | Language in template not in system | Use only allowed language names |
| `"CSRF verification failed"` | Missing X-CSRFToken header | Add CSRF header to all POST/PUT/DELETE |

---

## 🧑‍💻 Quick Fetch Template for All Requests

```javascript
// ─── Config ───────────────────────────────────────────────
const BASE_URL = 'http://localhost:8000';

function getCsrfToken() {
  return document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1] ?? '';
}

// ─── JSON API call ────────────────────────────────────────
async function apiCall(method, path, body = null) {
  const options = {
    method,
    credentials: 'include',
    headers: {
      'X-CSRFToken': getCsrfToken()
    }
  };
  if (body) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const resp = await fetch(BASE_URL + path, options);
  const json = await resp.json();
  if (json.error) throw new Error(json.error);
  return json.data;
}

// ─── File Upload call ─────────────────────────────────────
async function uploadFile(path, file, extraFields = {}) {
  const formData = new FormData();
  formData.append('file', file);
  Object.entries(extraFields).forEach(([k, v]) => formData.append(k, v));

  const resp = await fetch(BASE_URL + path, {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: formData
  });
  const json = await resp.json();
  if (json.error) throw new Error(json.error);
  return json.data;
}

// ─── Usage Examples ───────────────────────────────────────

// Login
await apiCall('POST', '/api/account/login/', { username: 'root', password: 'rootroot' });

// Upload test cases
const { id: testCaseId } = await uploadFile('/api/problem/admin/test_case/', zipFile, { spj: 'false' });

// Create problem
const problem = await apiCall('POST', '/api/problem/admin/problem/', {
  _id: '1001', title: 'A+B', test_case_id: testCaseId, /* ...other fields */
});

// Import batch ZIP
const { import_count } = await uploadFile('/api/problem/admin/import_problem/', batchZipFile);

// Import FPS XML
const { import_count } = await uploadFile('/api/problem/admin/import_fps/', fpsXmlFile);

// List problems
const { total, results } = await apiCall('GET', '/api/problem/admin/problem/?limit=20&offset=0');

// Delete problem
await apiCall('DELETE', '/api/problem/admin/problem/?id=5');
```

---

> 📌 **Live interactive API docs:** http://localhost:8000/swagger/  
> 📌 **Backup readable docs:** http://localhost:8000/redoc/  
> 📌 **All examples assume the server is running on `http://localhost:8000`**
