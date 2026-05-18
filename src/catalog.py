from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryProfile:
    name: str
    icon: str
    supplier_name: str
    region: str
    seasonality_type: str
    weekend_boost: float
    holiday_boost: float
    promo_boost: float
    price_sensitivity: float
    stockout_penalty: float
    delay_penalty: float
    reorder_days: int


CATEGORY_PROFILES: dict[str, CategoryProfile] = {
    "Бакалія": CategoryProfile("Бакалія", "🌾", "AgroTrade LLC", "Київ", "stable", 1.06, 1.18, 1.22, 0.26, 0.45, 0.08, 8),
    "Молочні продукти": CategoryProfile("Молочні продукти", "🥛", "MilkWay Supply", "Київ", "daily", 1.12, 1.15, 1.16, 0.22, 0.55, 0.12, 3),
    "Кондитерські вироби": CategoryProfile("Кондитерські вироби", "🍫", "Sweet Partner", "Львів", "holiday", 1.18, 1.35, 1.25, 0.3, 0.4, 0.05, 9),
    "Напої": CategoryProfile("Напої", "🥤", "Beverage Group", "Одеса", "summer", 1.16, 1.22, 1.2, 0.28, 0.38, 0.06, 7),
    "Побутова хімія": CategoryProfile("Побутова хімія", "🧴", "Clean Home Distribution", "Дніпро", "stable", 1.02, 1.08, 1.16, 0.18, 0.28, 0.05, 16),
    "Зоотовари": CategoryProfile("Зоотовари", "🐾", "Pet Family Trade", "Харків", "stable", 1.04, 1.06, 1.12, 0.16, 0.32, 0.05, 14),
    "Фрукти та овочі": CategoryProfile("Фрукти та овочі", "🍎", "Fresh Produce UA", "Вінниця", "harvest", 1.14, 1.18, 1.12, 0.2, 0.6, 0.11, 4),
    "Заморожені продукти": CategoryProfile("Заморожені продукти", "🧊", "Frozen Food Hub", "Київ", "winter", 1.09, 1.16, 1.18, 0.21, 0.35, 0.06, 10),
    "Товари для дому": CategoryProfile("Товари для дому", "🏠", "Home Comfort Trade", "Житомир", "stable", 1.05, 1.1, 1.12, 0.18, 0.25, 0.04, 18),
    "Гігієна": CategoryProfile("Гігієна", "🪥", "Care Retail Supply", "Київ", "stable", 1.03, 1.08, 1.12, 0.19, 0.28, 0.05, 12),
    "Кава та чай": CategoryProfile("Кава та чай", "☕", "Coffee Import Service", "Львів", "winter", 1.08, 1.12, 1.18, 0.24, 0.35, 0.06, 11),
    "Снеки": CategoryProfile("Снеки", "🥨", "Snack Distribution", "Одеса", "weekend", 1.22, 1.24, 1.2, 0.27, 0.3, 0.04, 8),
}


PRODUCT_DEFINITIONS: list[dict] = [
    {"product_name": "Рис довгозернистий 1 кг", "category": "Бакалія", "base_price": 68, "base_demand": 24, "shelf_life_days": 365},
    {"product_name": "Гречка ядриця 1 кг", "category": "Бакалія", "base_price": 79, "base_demand": 29, "shelf_life_days": 365},
    {"product_name": "Макарони спагеті 500 г", "category": "Бакалія", "base_price": 41, "base_demand": 31, "shelf_life_days": 365},
    {"product_name": "Олія соняшникова 1 л", "category": "Бакалія", "base_price": 74, "base_demand": 26, "shelf_life_days": 365},
    {"product_name": "Борошно пшеничне 2 кг", "category": "Бакалія", "base_price": 63, "base_demand": 22, "shelf_life_days": 365},
    {"product_name": "Цукор білий 1 кг", "category": "Бакалія", "base_price": 38, "base_demand": 33, "shelf_life_days": 365},
    {"product_name": "Сіль кухонна 1 кг", "category": "Бакалія", "base_price": 24, "base_demand": 18, "shelf_life_days": 365},
    {"product_name": "Вівсяні пластівці 800 г", "category": "Бакалія", "base_price": 58, "base_demand": 17, "shelf_life_days": 365},
    {"product_name": "Молоко 2.5% 1 л", "category": "Молочні продукти", "base_price": 46, "base_demand": 67, "shelf_life_days": 12},
    {"product_name": "Кефір 2.5% 900 мл", "category": "Молочні продукти", "base_price": 48, "base_demand": 48, "shelf_life_days": 10},
    {"product_name": "Йогурт полуничний 300 г", "category": "Молочні продукти", "base_price": 37, "base_demand": 39, "shelf_life_days": 14},
    {"product_name": "Сметана 20% 350 г", "category": "Молочні продукти", "base_price": 49, "base_demand": 27, "shelf_life_days": 14},
    {"product_name": "Масло вершкове 200 г", "category": "Молочні продукти", "base_price": 86, "base_demand": 19, "shelf_life_days": 45},
    {"product_name": "Сир твердий 200 г", "category": "Молочні продукти", "base_price": 92, "base_demand": 21, "shelf_life_days": 30},
    {"product_name": "Шоколад чорний 90 г", "category": "Кондитерські вироби", "base_price": 68, "base_demand": 35, "shelf_life_days": 240},
    {"product_name": "Шоколад молочний 90 г", "category": "Кондитерські вироби", "base_price": 65, "base_demand": 38, "shelf_life_days": 240},
    {"product_name": "Печиво вівсяне 300 г", "category": "Кондитерські вироби", "base_price": 49, "base_demand": 28, "shelf_life_days": 180},
    {"product_name": "Цукерки желейні 250 г", "category": "Кондитерські вироби", "base_price": 59, "base_demand": 25, "shelf_life_days": 180},
    {"product_name": "Торт вафельний 500 г", "category": "Кондитерські вироби", "base_price": 94, "base_demand": 16, "shelf_life_days": 120},
    {"product_name": "Батончик протеїновий 60 г", "category": "Кондитерські вироби", "base_price": 34, "base_demand": 20, "shelf_life_days": 240},
    {"product_name": "Вода мінеральна 1.5 л", "category": "Напої", "base_price": 27, "base_demand": 58, "shelf_life_days": 365},
    {"product_name": "Сік яблучний 1 л", "category": "Напої", "base_price": 54, "base_demand": 26, "shelf_life_days": 180},
    {"product_name": "Кола 2 л", "category": "Напої", "base_price": 49, "base_demand": 33, "shelf_life_days": 210},
    {"product_name": "Енергетичний напій 0.5 л", "category": "Напої", "base_price": 41, "base_demand": 22, "shelf_life_days": 240},
    {"product_name": "Лимонад 1 л", "category": "Напої", "base_price": 36, "base_demand": 29, "shelf_life_days": 180},
    {"product_name": "Холодний чай 0.5 л", "category": "Напої", "base_price": 32, "base_demand": 24, "shelf_life_days": 180},
    {"product_name": "Пральний порошок 3 кг", "category": "Побутова хімія", "base_price": 289, "base_demand": 10, "shelf_life_days": 720},
    {"product_name": "Капсули для прання 20 шт", "category": "Побутова хімія", "base_price": 248, "base_demand": 8, "shelf_life_days": 720},
    {"product_name": "Засіб для миття посуду 500 мл", "category": "Побутова хімія", "base_price": 73, "base_demand": 14, "shelf_life_days": 540},
    {"product_name": "Універсальний очищувач 750 мл", "category": "Побутова хімія", "base_price": 89, "base_demand": 9, "shelf_life_days": 540},
    {"product_name": "Відбілювач 1 л", "category": "Побутова хімія", "base_price": 61, "base_demand": 8, "shelf_life_days": 540},
    {"product_name": "Серветки для прибирання 3 шт", "category": "Побутова хімія", "base_price": 44, "base_demand": 12, "shelf_life_days": 720},
    {"product_name": "Корм для котів 1.5 кг", "category": "Зоотовари", "base_price": 234, "base_demand": 14, "shelf_life_days": 360},
    {"product_name": "Корм для собак 2 кг", "category": "Зоотовари", "base_price": 278, "base_demand": 12, "shelf_life_days": 360},
    {"product_name": "Наповнювач для котів 5 кг", "category": "Зоотовари", "base_price": 189, "base_demand": 10, "shelf_life_days": 720},
    {"product_name": "Ласощі для котів 60 г", "category": "Зоотовари", "base_price": 39, "base_demand": 17, "shelf_life_days": 360},
    {"product_name": "Ласощі для собак 100 г", "category": "Зоотовари", "base_price": 46, "base_demand": 15, "shelf_life_days": 360},
    {"product_name": "Шампунь для собак 250 мл", "category": "Зоотовари", "base_price": 112, "base_demand": 6, "shelf_life_days": 540},
    {"product_name": "Яблука українські 1 кг", "category": "Фрукти та овочі", "base_price": 41, "base_demand": 43, "shelf_life_days": 20},
    {"product_name": "Банани 1 кг", "category": "Фрукти та овочі", "base_price": 62, "base_demand": 39, "shelf_life_days": 10},
    {"product_name": "Картопля 1 кг", "category": "Фрукти та овочі", "base_price": 29, "base_demand": 34, "shelf_life_days": 45},
    {"product_name": "Томати 1 кг", "category": "Фрукти та овочі", "base_price": 78, "base_demand": 27, "shelf_life_days": 8},
    {"product_name": "Огірки 1 кг", "category": "Фрукти та овочі", "base_price": 74, "base_demand": 25, "shelf_life_days": 8},
    {"product_name": "Апельсини 1 кг", "category": "Фрукти та овочі", "base_price": 69, "base_demand": 21, "shelf_life_days": 15},
    {"product_name": "Заморожена піца", "category": "Заморожені продукти", "base_price": 126, "base_demand": 14, "shelf_life_days": 240},
    {"product_name": "Морозиво ванільне 500 г", "category": "Заморожені продукти", "base_price": 92, "base_demand": 18, "shelf_life_days": 180},
    {"product_name": "Заморожені овочі 400 г", "category": "Заморожені продукти", "base_price": 71, "base_demand": 15, "shelf_life_days": 240},
    {"product_name": "Пельмені домашні 800 г", "category": "Заморожені продукти", "base_price": 118, "base_demand": 20, "shelf_life_days": 180},
    {"product_name": "Нагетси курячі 400 г", "category": "Заморожені продукти", "base_price": 98, "base_demand": 16, "shelf_life_days": 180},
    {"product_name": "Лід харчовий 1 кг", "category": "Заморожені продукти", "base_price": 34, "base_demand": 11, "shelf_life_days": 365},
    {"product_name": "Паперові рушники 2 рулони", "category": "Товари для дому", "base_price": 58, "base_demand": 16, "shelf_life_days": 720},
    {"product_name": "Серветки столові 100 шт", "category": "Товари для дому", "base_price": 34, "base_demand": 18, "shelf_life_days": 720},
    {"product_name": "Свічки декоративні 4 шт", "category": "Товари для дому", "base_price": 66, "base_demand": 8, "shelf_life_days": 720},
    {"product_name": "Пакети для сміття 35 л 30 шт", "category": "Товари для дому", "base_price": 52, "base_demand": 14, "shelf_life_days": 720},
    {"product_name": "Губки кухонні 5 шт", "category": "Товари для дому", "base_price": 31, "base_demand": 15, "shelf_life_days": 720},
    {"product_name": "Контейнери харчові 3 шт", "category": "Товари для дому", "base_price": 79, "base_demand": 7, "shelf_life_days": 720},
    {"product_name": "Шампунь 400 мл", "category": "Гігієна", "base_demand": 15, "base_price": 112, "shelf_life_days": 540},
    {"product_name": "Зубна паста 100 мл", "category": "Гігієна", "base_price": 54, "base_demand": 18, "shelf_life_days": 540},
    {"product_name": "Мило рідке 500 мл", "category": "Гігієна", "base_price": 63, "base_demand": 16, "shelf_life_days": 540},
    {"product_name": "Гель для душу 500 мл", "category": "Гігієна", "base_price": 94, "base_demand": 13, "shelf_life_days": 540},
    {"product_name": "Піна для гоління 200 мл", "category": "Гігієна", "base_price": 102, "base_demand": 9, "shelf_life_days": 540},
    {"product_name": "Вологі серветки 72 шт", "category": "Гігієна", "base_price": 49, "base_demand": 22, "shelf_life_days": 540},
    {"product_name": "Кава мелена 250 г", "category": "Кава та чай", "base_price": 149, "base_demand": 19, "shelf_life_days": 360},
    {"product_name": "Кава зернова 1 кг", "category": "Кава та чай", "base_price": 489, "base_demand": 11, "shelf_life_days": 360},
    {"product_name": "Чай чорний 100 пакетиків", "category": "Кава та чай", "base_price": 118, "base_demand": 15, "shelf_life_days": 360},
    {"product_name": "Чай зелений 80 пакетиків", "category": "Кава та чай", "base_price": 106, "base_demand": 13, "shelf_life_days": 360},
    {"product_name": "Капучино розчинне 10 стіків", "category": "Кава та чай", "base_price": 78, "base_demand": 14, "shelf_life_days": 240},
    {"product_name": "Какао 250 г", "category": "Кава та чай", "base_price": 86, "base_demand": 10, "shelf_life_days": 360},
    {"product_name": "Чипси картопляні 140 г", "category": "Снеки", "base_price": 56, "base_demand": 29, "shelf_life_days": 210},
    {"product_name": "Горішки солоні 150 г", "category": "Снеки", "base_price": 64, "base_demand": 22, "shelf_life_days": 210},
    {"product_name": "Крекери сирні 180 г", "category": "Снеки", "base_price": 47, "base_demand": 19, "shelf_life_days": 210},
    {"product_name": "Попкорн карамельний 120 г", "category": "Снеки", "base_price": 44, "base_demand": 16, "shelf_life_days": 210},
    {"product_name": "Сухарики житні 100 г", "category": "Снеки", "base_price": 28, "base_demand": 21, "shelf_life_days": 210},
    {"product_name": "Мікс горіхів 200 г", "category": "Снеки", "base_price": 118, "base_demand": 13, "shelf_life_days": 210},
]


def build_product_catalog() -> list[dict]:
    catalog: list[dict] = []
    for index, product in enumerate(PRODUCT_DEFINITIONS, start=1):
        profile = CATEGORY_PROFILES[product["category"]]
        catalog.append(
            {
                "product_id": index,
                "product_name": product["product_name"],
                "category": product["category"],
                "product_icon": profile.icon,
                "base_price": product["base_price"],
                "base_demand": product["base_demand"],
                "seasonality_type": profile.seasonality_type,
                "shelf_life_days": product.get("shelf_life_days", 365),
                "supplier_name": profile.supplier_name,
                "region": profile.region,
            }
        )
    return catalog


def get_category_names() -> list[str]:
    return list(CATEGORY_PROFILES.keys())
