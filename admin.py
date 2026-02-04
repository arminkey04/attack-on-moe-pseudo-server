"""
Admin script for managing the AOM server.

Usage:
    python admin.py init                      - Initialize database with sample data
    python admin.py add-notice <image_url>    - Add a notice (requires valid image URL)
    python admin.py add-coupon                - Add a sample coupon
    python admin.py list-users                - List all users
    python admin.py clear-notices             - Clear all notices
    python admin.py user-info <user_id>       - Show user info and currency
    python admin.py set-ruby <user_id> <amount>       - Set user's ruby (萌魂)
    python admin.py set-gem <user_id> <amount>        - Set user's gem (钻石)
    python admin.py set-moecrystal <user_id> <amount> - Set user's moecrystal (梦水晶)
    python admin.py set-gold <user_id> <amount>       - Set user's gold (金币)
    python admin.py set-fp <user_id> <amount>         - Set user's friend point (好友点)
    python admin.py add-ruby <user_id> <amount>       - Add ruby to user
    python admin.py add-gem <user_id> <amount>        - Add gem to user
    python admin.py add-moecrystal <user_id> <amount> - Add moecrystal to user
    python admin.py add-gold <user_id> <amount>       - Add gold to user
    python admin.py add-fp <user_id> <amount>         - Add friend point to user

    === Mail/DropBox Commands (邮箱发放奖励) ===
    python admin.py send-mail <user_id> <type> <amount> [title] [msg]
        - Send mail reward to user
        - type: Gold, Gems, MoeCrystal, Ruby
        - Example: python admin.py send-mail abc123 Gems 100 "Daily Reward" "Thank you!"

    python admin.py send-mail-all <type> <amount> [title] [msg]
        - Send mail reward to ALL users
        - Example: python admin.py send-mail-all Gems 500 "Server Maintenance Compensation"

    python admin.py list-mail <user_id>       - List user's mail items
    python admin.py clear-mail <user_id>      - Clear user's mail items
"""

import asyncio
import sys
import json

from sqlalchemy import select
from database import async_session, init_db
from models.user import User, Session
from models.user_summary import UserSummary
from models.game_data import GameData
from models.notice import Notice
from models.drop_box import DropBox
from models.coupon import Coupon


async def init_database():
    """Initialize database with tables"""
    await init_db()
    print("Database initialized successfully!")


async def add_sample_notice(image_url: str = None):
    """Add a notice with image URL

    IMPORTANT: Notice MUST have a valid imageURL, otherwise the game client
    will hang when trying to download the image.

    Image requirements:
    - Must be a valid HTTP/HTTPS URL
    - Recommended size: 900x921 pixels
    - Format: PNG or JPG
    """
    if not image_url:
        print("ERROR: Notice requires a valid image URL!")
        print("Usage: python admin.py add-notice <image_url>")
        print("\nExample:")
        print("  python admin.py add-notice https://example.com/notice.png")
        return

    async with async_session() as db:
        notice = Notice(
            imageURL=image_url,
            order=1,
            text=json.dumps({
                "en": "Welcome to Attack on Moe Private Server!",
                "zh": "欢迎来到萌战私服！",
                "ja": "萌え戦争プライベートサーバーへようこそ！"
            }),
            url=""
        )
        db.add(notice)
        await db.commit()
        print(f"Notice added: {notice.objectId}")
        print(f"  Image URL: {notice.imageURL}")


async def add_sample_coupon():
    """Add a sample coupon"""
    async with async_session() as db:
        coupon = Coupon(
            code="WELCOME2024",
            relics=100,
            gems=500,
            unlockAdFree=False,
            maxRedemptions=-1  # Unlimited
        )
        db.add(coupon)
        await db.commit()
        print(f"Coupon added: {coupon.code}")
        print(f"  Relics: {coupon.relics}")
        print(f"  Gems: {coupon.gems}")


async def list_users():
    """List all users"""
    async with async_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            print("No users found.")
            return

        print(f"Found {len(users)} users:")
        for user in users:
            print(f"  - {user.objectId}: {user.username}")
            if user.email:
                print(f"    Email: {user.email}")
            if user.googleUserId:
                print(f"    Google ID: {user.googleUserId}")


async def add_sample_dropbox():
    """Add sample dropbox items - DEPRECATED: Use send-mail command instead"""
    print("DEPRECATED: add_sample_dropbox requires a user_id now.")
    print("Use 'python admin.py send-mail <user_id> <type> <amount>' instead.")


async def send_mail_reward(user_id: str, reward_type: str, amount: str, title: str = None, msg: str = None):
    """Send mail reward to a specific user

    Args:
        user_id: Target user's objectId
        reward_type: One of "Gold", "Gems", "MoeCrystal", "Ruby"
        amount: Amount as string
        title: Optional title (will use default if not provided)
        msg: Optional message
    """
    # Validate reward type
    valid_types = ["Gold", "Gems", "MoeCrystal", "Ruby", "Moetifacts", "MoetanPackages", "AdFree"]
    if reward_type not in valid_types:
        print(f"Invalid reward type: {reward_type}")
        print(f"Valid types: {', '.join(valid_types)}")
        return False

    # Default titles for each type
    default_titles = {
        "Gold": {"en": "Gold Reward", "zh": "金币奖励"},
        "Gems": {"en": "Gem Reward", "zh": "宝石奖励"},
        "MoeCrystal": {"en": "MoeCrystal Reward", "zh": "萌水晶奖励"},
        "Ruby": {"en": "Ruby Reward", "zh": "萌魂奖励"},
        "Moetifacts": {"en": "Artifact Reward", "zh": "神器奖励"},
        "MoetanPackages": {"en": "Character Package", "zh": "角色礼包"},
        "AdFree": {"en": "Ad-Free Privilege", "zh": "免广告特权"},
    }

    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.objectId == user_id))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {user_id}")
            return False

        # Create title
        if title:
            title_dict = {"en": title, "zh": title}
        else:
            title_dict = default_titles.get(reward_type, {"en": "Reward", "zh": "奖励"})

        # Create DropBox item
        drop_box = DropBox(
            userId=user_id,
            type=reward_type,
            title=json.dumps(title_dict),
            value=str(amount),
            msg=msg or ""
        )
        db.add(drop_box)
        await db.commit()

        print(f"Mail sent successfully!")
        print(f"  To: {user.username} ({user_id})")
        print(f"  Type: {reward_type}")
        print(f"  Amount: {amount}")
        print(f"  Title: {title_dict}")
        if msg:
            print(f"  Message: {msg}")
        print(f"  Mail ID: {drop_box.objectId}")
        return True


async def send_mail_to_all(reward_type: str, amount: str, title: str = None, msg: str = None):
    """Send mail reward to ALL users

    Args:
        reward_type: One of "Gold", "Gems", "MoeCrystal", "Ruby"
        amount: Amount as string
        title: Optional title
        msg: Optional message
    """
    async with async_session() as db:
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            print("No users found.")
            return

        print(f"Sending mail to {len(users)} users...")

        success_count = 0
        for user in users:
            result = await send_mail_reward(user.objectId, reward_type, amount, title, msg)
            if result:
                success_count += 1

        print(f"\nMail sent to {success_count}/{len(users)} users.")


async def list_user_mail(user_id: str):
    """List all mail items for a user"""
    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.objectId == user_id))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {user_id}")
            return

        # Get mail items
        result = await db.execute(select(DropBox).where(DropBox.userId == user_id))
        items = result.scalars().all()

        if not items:
            print(f"No mail items for user {user.username} ({user_id})")
            return

        print(f"\n=== Mail for {user.username} ({user_id}) ===")
        print(f"Total: {len(items)} items\n")

        for item in items:
            title_dict = {}
            if item.title:
                try:
                    title_dict = json.loads(item.title)
                except:
                    title_dict = {"en": item.title}

            print(f"  [{item.objectId}]")
            print(f"    Type: {item.type}")
            print(f"    Value: {item.value}")
            print(f"    Title: {title_dict.get('en', title_dict.get('zh', 'N/A'))}")
            if item.msg:
                print(f"    Message: {item.msg}")
            print(f"    Created: {item.createdAt}")
            print()


async def clear_user_mail(user_id: str):
    """Clear all mail items for a user"""
    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.objectId == user_id))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {user_id}")
            return

        # Get and delete mail items
        result = await db.execute(select(DropBox).where(DropBox.userId == user_id))
        items = result.scalars().all()

        count = len(items)
        for item in items:
            await db.delete(item)

        await db.commit()
        print(f"Cleared {count} mail items for user {user.username} ({user_id})")


async def clear_notices():
    """Clear all notices from database"""
    async with async_session() as db:
        result = await db.execute(select(Notice))
        notices = result.scalars().all()
        count = len(notices)
        for notice in notices:
            await db.delete(notice)
        await db.commit()
        print(f"Cleared {count} notices from database")


async def get_user_info(user_id: str):
    """Show user info and currency"""
    async with async_session() as db:
        # Find user
        result = await db.execute(select(User).where(User.objectId == user_id))
        user = result.scalar_one_or_none()

        if not user:
            print(f"User not found: {user_id}")
            return

        print(f"\n=== User Info ===")
        print(f"  Object ID: {user.objectId}")
        print(f"  Username: {user.username}")
        if user.email:
            print(f"  Email: {user.email}")
        if user.googleUserId:
            print(f"  Google ID: {user.googleUserId}")

        # Find user summary
        result = await db.execute(select(UserSummary).where(UserSummary.userId == user_id))
        summary = result.scalar_one_or_none()

        if summary:
            print(f"\n=== Currency (服务端 UserSummary) ===")
            print(f"  萌魂 (Ruby): {summary.ruby}")
            print(f"  钻石 (Gem): {summary.gem}")
            print(f"  梦水晶 (Moecrystal): {summary.moecrystal}")
            print(f"  好友点 (FriendPoint): {summary.friendPoint}")
            print(f"  好友上限 (FriendLimit): {summary.friendLimit}")
            print(f"  显示名称: {summary.displayName}")
        else:
            print(f"\n  No UserSummary found for this user")

        # Find game data for gold
        result = await db.execute(select(GameData).where(GameData.userId == user_id))
        game_data = result.scalar_one_or_none()

        if game_data and game_data.data:
            try:
                save_data = json.loads(game_data.data)
                print(f"\n=== Currency (服务端 GameData/云存档) ===")
                print(f"  金币 (Gold): {save_data.get('golds', 0)}")
                print(f"  关卡 (Stage): {save_data.get('stage', 0)}")
                print(f"  波次 (Wave): {save_data.get('wave', 0)}")
            except json.JSONDecodeError:
                print(f"\n  GameData exists but data is not valid JSON")
        else:
            print(f"\n  No GameData (云存档) found for this user")


async def set_currency(user_id: str, currency_type: str, amount: int):
    """Set user's currency to a specific amount"""
    async with async_session() as db:
        # Find user summary
        result = await db.execute(select(UserSummary).where(UserSummary.userId == user_id))
        summary = result.scalar_one_or_none()

        if not summary:
            # Check if user exists
            result = await db.execute(select(User).where(User.objectId == user_id))
            user = result.scalar_one_or_none()
            if not user:
                print(f"User not found: {user_id}")
                return
            # Create UserSummary if not exists
            summary = UserSummary(userId=user_id)
            db.add(summary)

        currency_names = {
            "ruby": "萌魂 (Ruby)",
            "gem": "钻石 (Gem)",
            "moecrystal": "梦水晶 (Moecrystal)",
            "fp": "好友点 (FriendPoint)"
        }

        if currency_type == "ruby":
            old_value = summary.ruby
            summary.ruby = amount
        elif currency_type == "gem":
            old_value = summary.gem
            summary.gem = amount
        elif currency_type == "moecrystal":
            old_value = summary.moecrystal
            summary.moecrystal = amount
        elif currency_type == "fp":
            old_value = summary.friendPoint
            summary.friendPoint = amount
        else:
            print(f"Unknown currency type: {currency_type}")
            print("Valid types: ruby, gem, moecrystal, fp")
            return

        await db.commit()
        print(f"Updated {currency_names[currency_type]} for user {user_id}")
        print(f"  {old_value} -> {amount}")


async def add_currency(user_id: str, currency_type: str, amount: int):
    """Add currency to user's balance"""
    async with async_session() as db:
        # Find user summary
        result = await db.execute(select(UserSummary).where(UserSummary.userId == user_id))
        summary = result.scalar_one_or_none()

        if not summary:
            # Check if user exists
            result = await db.execute(select(User).where(User.objectId == user_id))
            user = result.scalar_one_or_none()
            if not user:
                print(f"User not found: {user_id}")
                return
            # Create UserSummary if not exists
            summary = UserSummary(userId=user_id)
            db.add(summary)

        currency_names = {
            "ruby": "萌魂 (Ruby)",
            "gem": "钻石 (Gem)",
            "moecrystal": "梦水晶 (Moecrystal)",
            "fp": "好友点 (FriendPoint)"
        }

        if currency_type == "ruby":
            old_value = summary.ruby or 0
            summary.ruby = old_value + amount
            new_value = summary.ruby
        elif currency_type == "gem":
            old_value = summary.gem or 0
            summary.gem = old_value + amount
            new_value = summary.gem
        elif currency_type == "moecrystal":
            old_value = summary.moecrystal or 0
            summary.moecrystal = old_value + amount
            new_value = summary.moecrystal
        elif currency_type == "fp":
            old_value = summary.friendPoint or 0
            summary.friendPoint = old_value + amount
            new_value = summary.friendPoint
        else:
            print(f"Unknown currency type: {currency_type}")
            print("Valid types: ruby, gem, moecrystal, fp")
            return

        await db.commit()
        print(f"Added {amount} {currency_names[currency_type]} to user {user_id}")
        print(f"  {old_value} -> {new_value}")


async def set_gold(user_id: str, amount: float):
    """Set user's gold in GameData (云存档)"""
    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.objectId == user_id))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {user_id}")
            return

        # Find game data
        result = await db.execute(select(GameData).where(GameData.userId == user_id))
        game_data = result.scalar_one_or_none()

        if not game_data:
            # Create new GameData with default save data
            save_data = {"golds": amount}
            game_data = GameData(userId=user_id, data=json.dumps(save_data))
            db.add(game_data)
            old_value = 0
        else:
            try:
                save_data = json.loads(game_data.data) if game_data.data else {}
            except json.JSONDecodeError:
                save_data = {}
            old_value = save_data.get("golds", 0)
            save_data["golds"] = amount
            game_data.data = json.dumps(save_data)

        await db.commit()
        print(f"Updated 金币 (Gold) for user {user_id}")
        print(f"  {old_value} -> {amount}")
        print(f"\n注意: 金币同时存储在客户端本地，需要用户从云端加载存档才能生效")


async def add_gold(user_id: str, amount: float):
    """Add gold to user's GameData (云存档)"""
    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.objectId == user_id))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {user_id}")
            return

        # Find game data
        result = await db.execute(select(GameData).where(GameData.userId == user_id))
        game_data = result.scalar_one_or_none()

        if not game_data:
            # Create new GameData with default save data
            save_data = {"golds": amount}
            game_data = GameData(userId=user_id, data=json.dumps(save_data))
            db.add(game_data)
            old_value = 0
            new_value = amount
        else:
            try:
                save_data = json.loads(game_data.data) if game_data.data else {}
            except json.JSONDecodeError:
                save_data = {}
            old_value = save_data.get("golds", 0)
            new_value = old_value + amount
            save_data["golds"] = new_value
            game_data.data = json.dumps(save_data)

        await db.commit()
        print(f"Added {amount} 金币 (Gold) to user {user_id}")
        print(f"  {old_value} -> {new_value}")
        print(f"\n注意: 金币同时存储在客户端本地，需要用户从云端加载存档才能生效")


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == "init":
        await init_database()
        # Note: Not adding notices by default because they require valid image URLs
        # Use 'python admin.py add-notice <image_url>' to add notices manually
        await add_sample_coupon()
        await add_sample_dropbox()
        print("\nInitialization complete!")
        print("\nNote: No notices were added. To add a notice, use:")
        print("  python admin.py add-notice <image_url>")

    elif command == "add-notice":
        image_url = sys.argv[2] if len(sys.argv) > 2 else None
        await add_sample_notice(image_url)

    elif command == "clear-notices":
        await clear_notices()

    elif command == "add-coupon":
        await add_sample_coupon()

    elif command == "add-dropbox":
        await add_sample_dropbox()

    elif command == "list-users":
        await list_users()

    elif command == "user-info":
        if len(sys.argv) < 3:
            print("Usage: python admin.py user-info <user_id>")
            return
        await get_user_info(sys.argv[2])

    elif command == "set-ruby":
        if len(sys.argv) < 4:
            print("Usage: python admin.py set-ruby <user_id> <amount>")
            return
        await set_currency(sys.argv[2], "ruby", int(sys.argv[3]))

    elif command == "set-gem":
        if len(sys.argv) < 4:
            print("Usage: python admin.py set-gem <user_id> <amount>")
            return
        await set_currency(sys.argv[2], "gem", int(sys.argv[3]))

    elif command == "set-moecrystal":
        if len(sys.argv) < 4:
            print("Usage: python admin.py set-moecrystal <user_id> <amount>")
            return
        await set_currency(sys.argv[2], "moecrystal", int(sys.argv[3]))

    elif command == "add-ruby":
        if len(sys.argv) < 4:
            print("Usage: python admin.py add-ruby <user_id> <amount>")
            return
        await add_currency(sys.argv[2], "ruby", int(sys.argv[3]))

    elif command == "add-gem":
        if len(sys.argv) < 4:
            print("Usage: python admin.py add-gem <user_id> <amount>")
            return
        await add_currency(sys.argv[2], "gem", int(sys.argv[3]))

    elif command == "add-moecrystal":
        if len(sys.argv) < 4:
            print("Usage: python admin.py add-moecrystal <user_id> <amount>")
            return
        await add_currency(sys.argv[2], "moecrystal", int(sys.argv[3]))

    elif command == "set-gold":
        if len(sys.argv) < 4:
            print("Usage: python admin.py set-gold <user_id> <amount>")
            return
        await set_gold(sys.argv[2], float(sys.argv[3]))

    elif command == "add-gold":
        if len(sys.argv) < 4:
            print("Usage: python admin.py add-gold <user_id> <amount>")
            return
        await add_gold(sys.argv[2], float(sys.argv[3]))

    elif command == "set-fp":
        if len(sys.argv) < 4:
            print("Usage: python admin.py set-fp <user_id> <amount>")
            return
        await set_currency(sys.argv[2], "fp", int(sys.argv[3]))

    elif command == "add-fp":
        if len(sys.argv) < 4:
            print("Usage: python admin.py add-fp <user_id> <amount>")
            return
        await add_currency(sys.argv[2], "fp", int(sys.argv[3]))

    # === Mail/DropBox Commands ===
    elif command == "send-mail":
        if len(sys.argv) < 5:
            print("Usage: python admin.py send-mail <user_id> <type> <amount> [title] [msg]")
            print("Types: Gold, Gems, MoeCrystal, Ruby, Moetifacts, MoetanPackages, AdFree")
            print("Example: python admin.py send-mail abc123 Gems 100 \"Daily Reward\" \"Thank you!\"")
            return
        user_id = sys.argv[2]
        reward_type = sys.argv[3]
        amount = sys.argv[4]
        title = sys.argv[5] if len(sys.argv) > 5 else None
        msg = sys.argv[6] if len(sys.argv) > 6 else None
        await send_mail_reward(user_id, reward_type, amount, title, msg)

    elif command == "send-mail-all":
        if len(sys.argv) < 4:
            print("Usage: python admin.py send-mail-all <type> <amount> [title] [msg]")
            print("Types: Gold, Gems, MoeCrystal, Ruby")
            print("Example: python admin.py send-mail-all Gems 500 \"Server Compensation\"")
            return
        reward_type = sys.argv[2]
        amount = sys.argv[3]
        title = sys.argv[4] if len(sys.argv) > 4 else None
        msg = sys.argv[5] if len(sys.argv) > 5 else None
        await send_mail_to_all(reward_type, amount, title, msg)

    elif command == "list-mail":
        if len(sys.argv) < 3:
            print("Usage: python admin.py list-mail <user_id>")
            return
        await list_user_mail(sys.argv[2])

    elif command == "clear-mail":
        if len(sys.argv) < 3:
            print("Usage: python admin.py clear-mail <user_id>")
            return
        await clear_user_mail(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
