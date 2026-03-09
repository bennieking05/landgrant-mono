# Jira Acceptance Criteria Template

This document provides standard templates for writing acceptance criteria in Jira stories and epics.

---

## Why Acceptance Criteria?

- **Clarity**: Defines what "done" means for each item
- **Testability**: Each criterion can be verified
- **Alignment**: Ensures team and stakeholders agree on scope
- **Quality**: Prevents incomplete deliverables

---

## Format

Use Jira's task list format (checkboxes) for acceptance criteria:

```
### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
```

---

## Templates by Issue Type

### Epic Acceptance Criteria

```markdown
### Acceptance Criteria

**Completeness**
- [ ] All child stories completed and verified
- [ ] No open blockers or critical bugs

**Documentation**
- [ ] Technical documentation updated
- [ ] API documentation current
- [ ] User-facing documentation reviewed

**Quality**
- [ ] E2E tests passing for all workflows
- [ ] Code reviewed and merged to main
- [ ] No critical linter errors

**Deployment**
- [ ] Deployed to staging environment
- [ ] Smoke tests passing on staging
- [ ] UAT sign-off received from stakeholders

**Compliance**
- [ ] Security review completed (if applicable)
- [ ] Audit logging verified
```

### Story/Task Acceptance Criteria

```markdown
### Acceptance Criteria

**Functionality**
- [ ] Feature implemented per requirements
- [ ] Edge cases handled appropriately
- [ ] Error messages are user-friendly

**Code Quality**
- [ ] Unit tests written (coverage >= 80%)
- [ ] Code reviewed and approved
- [ ] No critical linter/TypeScript errors
- [ ] Follows project coding standards

**Documentation**
- [ ] Code comments for complex logic
- [ ] README updated if needed
- [ ] API docs updated if endpoints changed

**Testing**
- [ ] Manual testing completed
- [ ] Integration tests passing
- [ ] No regression in existing features
```

### Bug Fix Acceptance Criteria

```markdown
### Acceptance Criteria

**Resolution**
- [ ] Root cause identified and documented
- [ ] Fix implemented and verified
- [ ] Original bug scenario no longer reproduces

**Regression**
- [ ] Related functionality tested
- [ ] No new issues introduced
- [ ] Existing tests still passing

**Prevention**
- [ ] Test added to prevent regression
- [ ] Similar code patterns reviewed for same issue
```

### Documentation Task Acceptance Criteria

```markdown
### Acceptance Criteria

**Content**
- [ ] Information is accurate and current
- [ ] Covers all required topics
- [ ] Examples provided where helpful

**Quality**
- [ ] Spelling and grammar checked
- [ ] Formatting consistent with style guide
- [ ] All links verified to work

**Accessibility**
- [ ] Easy to find from documentation index
- [ ] Logical organization and headings
- [ ] Searchable keywords included
```

### API Endpoint Acceptance Criteria

```markdown
### Acceptance Criteria

**Functionality**
- [ ] Endpoint returns correct data
- [ ] Request validation works
- [ ] Error responses follow API conventions

**Security**
- [ ] RBAC authorization enforced
- [ ] Input sanitized against injection
- [ ] Rate limiting applied

**Documentation**
- [ ] OpenAPI spec updated
- [ ] Request/response examples documented
- [ ] Error codes documented

**Testing**
- [ ] Unit tests for business logic
- [ ] Integration tests for endpoint
- [ ] Edge cases covered
```

### UI Component Acceptance Criteria

```markdown
### Acceptance Criteria

**Functionality**
- [ ] Component renders correctly
- [ ] User interactions work as expected
- [ ] State management correct

**Design**
- [ ] Matches design specs/mockups
- [ ] Responsive on desktop and tablet
- [ ] Follows design system patterns

**Accessibility**
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] Color contrast meets WCAG 2.1 AA

**Testing**
- [ ] Component tests passing
- [ ] E2E tests for critical paths
- [ ] Visual regression baseline captured
```

---

## Best Practices

### DO

- Write specific, measurable criteria
- Use action verbs (implemented, verified, documented)
- Keep criteria independent and testable
- Include non-functional requirements (performance, security)
- Update criteria if scope changes

### DON'T

- Write vague criteria ("works correctly")
- Include implementation details
- Add criteria that can't be verified
- Forget about edge cases and error handling
- Skip documentation and testing criteria

---

## Examples

### Good Acceptance Criteria

```markdown
- [ ] User can upload files up to 10MB in size
- [ ] Uploaded files are scanned for viruses before storage
- [ ] Progress indicator shows upload percentage
- [ ] Error message displayed if upload fails with retry option
- [ ] Uploaded files appear in the document list within 5 seconds
```

### Poor Acceptance Criteria

```markdown
- [ ] Upload works
- [ ] Files are handled properly
- [ ] Good user experience
```

---

## Quick Reference

| Issue Type | Key Criteria Categories |
|------------|------------------------|
| Epic | Completeness, Documentation, Quality, Deployment, Compliance |
| Story | Functionality, Code Quality, Documentation, Testing |
| Bug | Resolution, Regression, Prevention |
| Docs | Content, Quality, Accessibility |
| API | Functionality, Security, Documentation, Testing |
| UI | Functionality, Design, Accessibility, Testing |

---

## Jira ADF Format

When adding acceptance criteria via API, use this Atlassian Document Format:

```json
{
  "type": "taskList",
  "attrs": {"localId": "ac-unique-id"},
  "content": [
    {
      "type": "taskItem",
      "attrs": {"localId": "item-1", "state": "TODO"},
      "content": [{"type": "text", "text": "Criterion text here"}]
    }
  ]
}
```

State values: `TODO`, `DONE`

---

*Last updated: February 2026*
