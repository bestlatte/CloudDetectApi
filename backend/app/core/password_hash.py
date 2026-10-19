import getpass

from argon2 import PasswordHasher


def main() -> None:
    password = getpass.getpass("Admin password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password or password != confirmation:
        raise SystemExit("Passwords are empty or do not match.")
    print(PasswordHasher().hash(password))


if __name__ == "__main__":
    main()

