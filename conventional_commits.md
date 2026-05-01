# Conventional Commits - Chuẩn Viết Commit Message

## Định nghĩa
Conventional Commits là một quy ước viết commit message có cấu trúc rõ ràng, giúp tự động hóa changelog, versioning và dễ đọc lịch sử dự án.

---

## Cấu trúc tổng quát

```
<type>(<scope>): <subject>

[body]

[footer]
```

- **type**: Loại thay đổi (bắt buộc)
- **scope**: Phạm vi ảnh hưởng (tùy chọn)
- **subject**: Mô tả ngắn gọn (bắt buộc)
- **body**: Mô tả chi tiết (tùy chọn)
- **footer**: Ghi chú thêm, breaking change, issue reference (tùy chọn)

---

## Danh sách type

| Type | Ý nghĩa | Ảnh hưởng version |
|------|---------|-------------------|
| `feat` | Tính năng mới | MINOR |
| `fix` | Sửa bug | PATCH |
| `docs` | Chỉ thay đổi tài liệu | Không tăng |
| `style` | Format, dấu chấm phẩy, không đổi logic | Không tăng |
| `refactor` | Tái cấu trúc code, không thêm tính năng hay sửa bug | Không tăng |
| `test` | Thêm hoặc sửa test | Không tăng |
| `chore` | Cập nhật build, dependency, công việc bảo trì | Không tăng |
| `perf` | Cải thiện hiệu suất | PATCH |
| `ci` | Thay đổi cấu hình CI/CD | Không tăng |
| `build` | Thay đổi hệ thống build hoặc dependency ngoài | Không tăng |
| `revert` | Hoàn tác một commit trước đó | Tùy |

---

## Quy tắc viết subject

- Dùng thì hiện tại, thể chủ động: `add`, `fix`, `update` (không phải `added`, `fixed`)
- Không viết hoa chữ cái đầu
- Không kết thúc bằng dấu chấm (`.`)
- Tối đa 72 ký tự
- Viết bằng tiếng Anh (khuyến nghị) hoặc tiếng Việt nhất quán

---

## Ví dụ cơ bản

```bash
feat: add user login feature
fix: correct email validation logic
docs: update README installation guide
style: reformat according to eslint rules
refactor: extract helper functions to utils
test: add unit tests for auth module
chore: update dependencies to latest versions
```

---

## Ví dụ có scope

```bash
feat(auth): add JWT token refresh
fix(api): handle null response from payment gateway
docs(readme): add environment setup section
style(button): fix padding inconsistency
test(cart): add integration test for checkout flow
chore(deps): upgrade react to v18
```

---

## Ví dụ có body

```
fix(auth): prevent session from expiring prematurely

The session timeout was calculated from creation time instead of
last activity time. Updated logic to reset the timer on each
valid user action.
```

---

## Ví dụ có footer

```
feat(payment): add support for VNPay gateway

Integrated VNPay API for domestic payment processing.
Supports one-time and recurring payments.

Closes #142
Reviewed-by: Nguyen Van A
```

---

## Breaking Change

Khi thay đổi gây không tương thích ngược (breaking change), thêm `BREAKING CHANGE:` vào footer hoặc dấu `!` sau type/scope.

```bash
# Cách 1: dấu !
feat!: remove deprecated login endpoint

# Cách 2: footer BREAKING CHANGE
feat(api)!: change response format to JSON:API spec

BREAKING CHANGE: all API responses now follow JSON:API specification.
Clients must update their parsers accordingly.
```

Breaking change sẽ tăng version MAJOR.

---

## Semantic Versioning tương ứng

```
fix      → PATCH   (1.0.0 → 1.0.1)
feat     → MINOR   (1.0.0 → 1.1.0)
BREAKING → MAJOR   (1.0.0 → 2.0.0)
```

---

## Ví dụ thực tế theo dự án

### Dự án web app

```bash
feat(ui): add dark mode toggle
fix(form): fix required field not triggering validation
perf(image): lazy load product images on homepage
refactor(store): migrate from Redux to Zustand
chore(ci): add GitHub Actions workflow for deployment
```

### Dự án API backend

```bash
feat(endpoint): add GET /users/:id route
fix(middleware): fix CORS headers missing on preflight
docs(swagger): update OpenAPI spec for v2 endpoints
test(auth): add test cases for token expiry
build(docker): optimize Dockerfile layer caching
```

### Dự án mobile

```bash
feat(screen): add onboarding flow for new users
fix(android): fix crash on back press in payment screen
style(theme): update primary color to match brand guideline
chore(gradle): update build tools version
```

---

## Lỗi thường gặp cần tránh

| Sai | Đúng |
|-----|------|
| `Fixed bug` | `fix: resolve null pointer in user service` |
| `update` | `chore: update lodash to 4.17.21` |
| `WIP` | `feat(profile): add avatar upload (wip)` |
| `fix stuff` | `fix(cart): recalculate total after coupon applied` |
| `FEATURE: Login` | `feat(auth): add email and password login` |

---

## Công cụ hỗ trợ

| Công cụ | Mục đích |
|---------|---------|
| `commitizen` | CLI giúp viết commit đúng chuẩn |
| `commitlint` | Lint kiểm tra commit message |
| `standard-version` | Tự động tạo CHANGELOG và bump version |
| `semantic-release` | Tự động release dựa trên commit |
| `husky` | Chạy commitlint trước khi commit |

---

## Tham khảo

- Đặc tả chính thức: https://www.conventionalcommits.org
- Angular commit guidelines: https://github.com/angular/angular/blob/main/CONTRIBUTING.md
- Semantic Versioning: https://semver.org
