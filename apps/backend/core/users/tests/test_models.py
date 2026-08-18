from core.users.models import User


def test_user_name():
    user = User(name="Ada Lovelace")

    assert user.name == "Ada Lovelace"
