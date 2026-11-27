# Auth testing — GénéraQuiz (custom JWT + bcrypt, cookies)
- Credentials: /app/memory/test_credentials.md (TEST_ADMIN_EMAIL / TEST_ADMIN_PASSWORD in /app/backend/.env).
- Endpoints: POST /api/auth/register, /api/auth/login, GET /api/auth/me, POST /api/auth/verify-email {token}, POST /api/auth/resend-verification (3/h per user), PATCH /api/auth/profile {name, email?, current_password?}.
- Verification tokens are stored hashed (sha256) in db.email_verify_tokens {token_hash, user_id, email, expires_at, used}. To test the page, insert a doc with a known token and open /verifier-email?token=<token>.
- Social linking: routers/social_auth._upsert_social_user — linking Google/Apple to an UNVERIFIED account wipes its password_hash and bumps token_version.
- Rate limits live in db.rate_limits — clear with delete_many({}) if 429.
