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
# Authorization Model

## Mental Model

Authorization can be understood as 4 layers:

```text
ROLE
  ↓
PERMISSIONS
  ↓
RESTRICTIONS
  ↓
DATA VISIBILITY
```

# Authorization System 

---

# The 4 Layers of Authorization

```text
ROLE
  ↓
PERMISSIONS
  ↓
RESTRICTIONS
  ↓
DATA VISIBILITY
```

---

## 1. ROLE

A role is the user's identity inside the system.

Example roles:

- admin
- doctor
- nurse
- billing

Think:

```text
Role = Job Type
```

---

## 2. PERMISSIONS

Permissions define what the role is ALLOWED to do.

Example:

```js
allow: ['patients_read']
```

Meaning:

```text
This user can read patient records
```

---

## 3. RESTRICTIONS

Restrictions define what the role is NOT allowed to do.

Example:

```js
deny: ['encounters_close']
```

Meaning:

```text
This user CANNOT close encounters
```

Even if they can read or edit encounters.

---

## 4. DATA VISIBILITY

Some users can see all data.

Some users only see partial data.

Example:

```js
mask: ['patient_demographics']
```

Meaning:

```text
Hide sensitive patient information
```

---

# Role Breakdown

---

# 1. Admin

## Permissions

```js
allow: ['all']
```

---

## What This Means

Admin is the superuser.

They can:

- Access all endpoints
- Perform all actions
- View all data
- Ignore most restrictions

Think:

```text
Admin = Game Master
```

---

# 2. Doctor

## Permissions

```js
allow: ['all']
```

---

## What Doctors Can Do

Doctors can:

- Read patient records
- Update encounters
- Close encounters
- Write prescriptions
- Access medical workflows

---

## Data Visibility

```js
mask: []
```

Meaning:

```text
Nothing is hidden from doctors
```

Doctors can see all patient information.

---

# 3. Nurse

Nurses have LIMITED permissions.

They can do some things.

They cannot do others.

---

## Allowed Actions

```js
allow: [
  'patients_read',
  'encounters_read',
  'encounters_observations'
]
```

---

## Nurse CAN

- Read patient data
- Read encounters
- Add observations
- Create prescriptions

Think:

```text
Nurse can help manage care
BUT cannot finalize everything
```

---

## Denied Actions

```js
deny: [
  'encounters_close',
  'billing_all'
]
```

---

## Nurse CANNOT

- Close encounters
- Process billing
- Access billing workflows

Meaning:

```text
Some actions require higher authority
```

---

# Data Masking

## Masked Fields

```js
mask: [
  'patient_demographics'
]
```

---

## What This Means

Some sensitive information is hidden from nurses.

For example:

- patient name
- address
- demographic info

---

# Example Masked Response

```json
{
  "name": "*** hidden ***",
  "address": "*** hidden ***",
  "medical_notes": "visible"
}
```

Meaning:

```text
Nurse can still do medical work
BUT cannot see sensitive identity data
```

---

# Authorization Evaluation Flow

When a request enters the system:

```text
User Request
     ↓
Identify User Role
     ↓
Load RBAC Rules
     ↓
Check allow[]
     ↓
Check deny[]
     ↓
Check workflow state
     ↓
Apply masking rules
     ↓
Return final response
```

---

# Real Meaning of This Flow

The system asks questions in order:

---

## Step 1

```text
Who is this user?
```

Example:

```text
nurse
doctor
admin
```

---

## Step 2

```text
What are they allowed to do?
```

Example:

```js
allow: ['patients_read']
```

---

## Step 3

```text
What are they blocked from doing?
```

Example:

```js
deny: ['billing_all']
```

---

## Step 4

```text
Is the workflow state valid?
```

Example:

Maybe encounters can ONLY close when:

```text
status === READY_FOR_CLOSE
```

Even doctors may fail if workflow state is invalid.

---

## Step 5

```text
Should some data be hidden?
```

Example:

```js
mask: ['patient_demographics']
```

---

# Important Technical Idea

Authorization is NOT just:

```text
Can user access endpoint?
```

It is ALSO:

- What actions can they perform?
- What actions are blocked?
- What data can they see?
- What workflow state is required?
- What business rules apply?

---

# Final Mental Model

Think of authorization as:

```text
WHO
  can do
WHAT
  under WHICH CONDITIONS
  while seeing WHICH DATA
```

