import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, func

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.database import AsyncSessionLocal
from backend.models import User, MobileSale, InternetSale

async def check_status():
    async with AsyncSessionLocal() as session:
        # 1. Simulyatsiya qilingan userlar bormi?
        users_count = await session.execute(select(func.count(User.tg_id)).where(User.is_simulated == True))
        fake_users = users_count.scalar()
        
        # 2. Bazada savdolar bormi?
        mob_count = await session.execute(select(func.count(MobileSale.id)))
        int_count = await session.execute(select(func.count(InternetSale.id)))
        
        print(f"Simulyatsiya userlari (Fake Users): {fake_users} ta")
        print(f"Mobil savdolar bazada: {mob_count.scalar()} ta")
        print(f"Internet savdolar bazada: {int_count.scalar()} ta")
        
        if fake_users == 0:
            print("\n⚠️ DIQQAT: Bazada simulyatsiya uchun foydalanuvchi yo'q! Hozir 100 ta yaratamiz...")
            for i in range(1, 101):
                new_user = User(
                    tg_id=1000 + i, 
                    full_name=f"Simulated User #{i}",
                    is_simulated=True,
                    lang="uz"
                )
                session.add(new_user)
            await session.commit()
            print("✅ 100 ta Fake User yaratildi. Endi Engine ishlaydi!")

if __name__ == "__main__":
    asyncio.run(check_status())
