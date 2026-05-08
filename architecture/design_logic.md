# RBAC Exploration Notes

## Goal

Understand **why certain user roles can or cannot perform specific jobs/actions**.

We want to explore:

- Who can do what
- Which API endpoints are allowed
- Which actions are blocked
- Which data is masked
- Which workflow states are required

---

# Core Questions

For each role:

1. What actions are allowed?
2. What actions are denied?
3. What API endpoints are accessible?
4. What data fields are masked?
5. What workflow states are required before an action is permitted?

---

# Example Permission Matrix

| Role    | Action                          | Result      |
|----------|----------------------------------|-------------|
| doctor   | close encounter                  | ✅ Allowed  |
| nurse    | export record                    | ❌ Denied   |
| nurse    | export payment                   | ❌ Denied   |
| billing  | process payment                  | ✅ Allowed  |
| admin    | export records                   | ✅ Allowed  |

---

# RBAC Logic Structure

```js
const rbac = {
  doctor: {
    allow: ['all'],
    mask: []
  },

  nurse: {
    allow: [
      'patients_read',
      'encounters_read',
      'encounters_observations'
    ],

    deny: [
      'encounters_close',
      'billing_all'
    ],

    mask: [
      'patient_demographics'
    ]
  }
}
```


Mental Model

Think of authorization as 4 layers:

ROLE
  ↓
PERMISSIONS
  ↓
RESTRICTIONS
  ↓
DATA VISIBILITY
Role Breakdown
Admin
Permissions
allow: ['all']
Meaning

Admin can:

Access all endpoints
Perform all actions
View all data
Bypass most restrictions
Doctor
Permissions
allow: ['all']
Meaning

Doctor can:

Read patient records
Update encounters
Close encounters
Write prescriptions
Access medical workflows
Data Visibility
mask: []

No masked fields.

Nurse
Allowed Actions
allow: [
  'patients_read',
  'encounters_read',
  'encounters_observations'
]

Nurse CAN:

Read patient data
Read encounters
Add observations
Create prescriptions
Denied Actions
deny: [
  'encounters_close',
  'billing_all'
]

Nurse CANNOT:

Close encounters
Process billing
Access billing workflows
Masked Data
mask: [
  'patient_demographics'
]

When a nurse views records:

Certain patient fields are hidden
Sensitive demographic data is masked

Example:

{
  "name": "*** hidden ***",
  "address": "*** hidden ***",
  "medical_notes": "visible"
}
Authorization Evaluation Flow
User Role
   ↓
Load RBAC Rules
   ↓
Check allow[]
   ↓
Check deny[]
   ↓
Check workflow state
   ↓
Apply data masking
   ↓
Return final response
