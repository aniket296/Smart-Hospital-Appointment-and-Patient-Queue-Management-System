"""Script to generate deterministic Werkzeug password hashes for seed.sql."""

from werkzeug.security import generate_password_hash


DEFAULT_ACCOUNTS = [
    ("admin@hospital.test", "Admin@123"),
    ("doctor1@hospital.test", "Doctor@123"),
    ("doctor2@hospital.test", "Doctor@123"),
    ("doctor3@hospital.test", "Doctor@123"),
    ("patient1@hospital.test", "Patient@123"),
    ("patient2@hospital.test", "Patient@123"),
    ("patient3@hospital.test", "Patient@123"),
]


def generate_hashes():
    """Return a dict mapping email to a Werkzeug password hash."""
    results = {}
    for email, password in DEFAULT_ACCOUNTS:
        results[email] = generate_password_hash(password, method="scrypt")
    return results


def main():
    hashes = generate_hashes()
    print("-- Generated Werkzeug Password Hashes for seed.sql")
    for email, pw_hash in hashes.items():
        print(f"-- {email}: {pw_hash}")


if __name__ == "__main__":
    main()
