# Опис бази даних

## Призначення
SQLite база даних демонструє структуру даних дипломного прототипу та використовується для зберігання імпортованих продажів, товарів, метрик і рекомендацій.

## Таблиці

### `users`
- `id`
- `username`
- `password_hash`
- `role`
- `created_at`

Призначення: зберігання користувачів системи.

### `products`
- `id`
- `name`
- `category`
- `product_icon`
- `price`
- `stock_quantity`
- `base_demand`
- `seasonality_type`
- `shelf_life_days`
- `supplier_name`
- `region`

Призначення: довідник товарів та їх актуальних характеристик.

### `sales`
- `id`
- `product_id`
- `date`
- `quantity`
- `price`
- `stock_quantity`
- `promo`
- `holiday`
- `supplier_delay_days`

Призначення: історичні записи продажів.

### `forecasts`
- `id`
- `product_id`
- `forecast_date`
- `predicted_quantity`
- `created_at`

Призначення: історія сформованих прогнозів.

### `model_metrics`
- `id`
- `model_name`
- `mae`
- `rmse`
- `mape`
- `created_at`
- `raw_metrics_json`

Призначення: історія навчання моделей і збереження метрик.

### `imports`
- `id`
- `filename`
- `rows_count`
- `products_count`
- `imported_at`
- `status`
- `error_message`

Призначення: журнал імпортів CSV.

### `recommendations`
- `id`
- `product_id`
- `forecast_days`
- `forecast_quantity`
- `current_stock`
- `safety_stock`
- `recommended_order_quantity`
- `explanation`
- `priority`
- `created_at`

Призначення: історія рекомендацій закупівель.

## Зв’язки
- `sales.product_id -> products.id`
- `forecasts.product_id -> products.id`
- `recommendations.product_id -> products.id`

## ER-структура текстом
Один товар з таблиці `products` може мати багато записів у `sales`, багато сформованих прогнозів у `forecasts` і багато рекомендацій у `recommendations`. Таблиця `imports` зберігає службову історію імпорту, а `model_metrics` — історію навчання моделей.

## Формат CSV для імпорту
### Обов’язкові колонки
- `date`
- `product_id`
- `product_name`
- `category`
- `sales_quantity`
- `price`
- `stock_quantity`
- `promo`
- `holiday`
- `supplier_delay_days`

### Додаткові колонки
- `product_icon`
- `shelf_life_days`
- `supplier_name`
- `region`
