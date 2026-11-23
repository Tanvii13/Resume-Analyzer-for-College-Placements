"""Shared test set-up (Sprint 6).
CSRF tokens are switched off for the Sprint 1 tests, which post forms directly like a script would.
tests/test_sprint6.py switches them back on to test them. Login limits and logs start fresh every test, with a test student account."""
import pytest
from werkzeug.security import generate_password_hash

import app as app_module

# The app no longer ships with a demo student. The tests create their own before each test.
TEST_STUDENT = {"name": "Alex Rivera", "email": "alex.rivera@dau.ac.in",
                "password_hash": generate_password_hash("Password@123"), "role": "student"}


@pytest.fixture(autouse=True)
def fresh_security_state():
    app_module.app.config["CSRF_ENABLED"] = False
    app_module.USERS[TEST_STUDENT["email"]] = dict(TEST_STUDENT)
    for store in (app_module.LOGIN_FAILS, app_module.ACCESS_LOG, app_module.AUDIT_LOG,
                  app_module.REVIEWS, app_module.FAIRNESS_ISSUES, app_module.FAIRNESS_RUNS):
        store.clear()
    yield
    app_module.app.config["CSRF_ENABLED"] = True
    app_module.USERS.pop(TEST_STUDENT["email"], None)
