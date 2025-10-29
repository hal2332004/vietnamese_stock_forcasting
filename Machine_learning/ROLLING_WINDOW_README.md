# 🔄 Rolling Window Time Series Forecasting - No Data Leakage

## 📋 Overview

Notebook đã được refactor hoàn toàn để sử dụng **Rolling Window** với chiến lược train-test split đơn giản và rõ ràng, **đảm bảo 100% không bị data leakage**.

---

## 🎯 Configuration

### Window Sizes
- **14 days** - Rolling window 2 tuần
- **30 days** - Rolling window 1 tháng

### Train-Test Split
```
|=================== TRAINING (~9+ years) ===================|== TEST (30 days) ==|
Day 1                                               Day N-30  Day N-29         Day N
                                                        ↑
                                                  SPLIT POINT
                                            (No Data Leakage Boundary)
```

### Key Parameters
- **Training**: All data EXCEPT last 30 days (~9+ years)
- **Testing**: Last 30 days only
- **Models**: LinearRegression, RandomForest, XGBoost, CatBoost, SVR
- **Stocks**: ACB, BID, VCB, MBB, FPT

---

## 🔒 Data Leakage Prevention Strategy

### 1. Clean Train-Test Split

```python
def split_train_test_no_leakage(data, test_days=30):
    split_index = len(data) - test_days
    train_data = data[:split_index]      # All except last 30 days
    test_data = data[split_index:]       # Last 30 days only
    return train_data, test_data, split_index
```

**Đảm bảo:**
- ✅ Không có overlap giữa train và test
- ✅ Test data hoàn toàn tách biệt
- ✅ Temporal order được giữ nguyên

### 2. Rolling Window on Training Data Only

```python
def create_rolling_window_sequences(data, window_size):
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:i+window_size])      # Past window_size days
        y.append(data[i+window_size])        # Next day
    return np.array(X), np.array(y)
```

**Example với window_size=14:**
```
Training Data: [Day 1, Day 2, ..., Day 2500]

Sample 1: [Day 1  → Day 14]  → Predict Day 15
Sample 2: [Day 2  → Day 15]  → Predict Day 16
Sample 3: [Day 3  → Day 16]  → Predict Day 17
...
Sample N: [Day 2486 → Day 2499] → Predict Day 2500
```

**Đảm bảo:**
- ✅ Rolling window CHỈ áp dụng trong training data
- ✅ Không sử dụng test data trong quá trình tạo sequences
- ✅ Mỗi sample chỉ nhìn thấy quá khứ

### 3. Recursive Forecasting on Test Set

```python
def recursive_forecast(model, initial_window, n_steps, scaler=None):
    predictions = []
    current_window = initial_window.copy()  # Last window_size from training
    
    for _ in range(n_steps):
        pred = model.predict(current_window.reshape(1, -1))[0]
        predictions.append(pred)
        # Roll window: remove oldest, add prediction
        current_window = np.append(current_window[1:], pred)
    
    return np.array(predictions)
```

**Process:**
1. Bắt đầu với window_size ngày cuối của training data
2. Predict ngày đầu tiên của test set
3. Add prediction vào window, remove giá trị cũ nhất
4. Lặp lại cho 30 ngày test

**Đảm bảo:**
- ✅ Không sử dụng actual test values trong prediction
- ✅ Mỗi prediction dựa trên window chứa predictions trước đó
- ✅ Mô phỏng chính xác real-world forecasting

---

## 📊 Visualization & Verification

### 1. Train-Test Split Visualization

Notebook tự động tạo visualization cho mỗi stock:
- **Upper plot**: Full time series với train/test được highlight
- **Lower plot**: Timeline view với clear boundary
- **Statistics**: Detailed summary về split

**Kiểm tra:**
- ✅ Visual confirmation không có overlap
- ✅ Split point rõ ràng
- ✅ Date ranges chính xác

### 2. Rolling Window Mechanism Visualization

Shows how rolling window creates training samples:
- Multiple examples của window rolling
- Input features (past N days) → Output target (next day)
- Clear visualization của temporal structure

**Kiểm tra:**
- ✅ Window chỉ chứa past data
- ✅ Target luôn là future value
- ✅ No overlap với test data

---

## 🚀 Training Pipeline

### Step-by-Step Process

```python
# 1. Load data
df_raw = pd.read_csv("stock_data_2025_raw.csv")

# 2. Split train-test (NO LEAKAGE)
train_data, test_data, split_idx = split_train_test_no_leakage(
    close_prices, 
    test_days=30
)

# 3. Create rolling window sequences from TRAINING ONLY
X_train, y_train = create_rolling_window_sequences(train_data, window_size=14)

# 4. Train model
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
model.fit(X_train_scaled, y_train)

# 5. Recursive forecast on TEST
initial_window = train_data[-window_size:]
predictions = recursive_forecast(model, initial_window, n_steps=30, scaler=scaler)

# 6. Evaluate
metrics = evaluate_metrics(test_data, predictions)
```

### Full Pipeline Function

```python
result = train_and_forecast_rolling_window(
    df=df_raw,
    symbol='ACB',
    model_name='XGBRegressor',
    model=XGBRegressor(),
    window_size=14,
    test_days=30,
    use_scaling=True
)
```

**Returns:**
- Training statistics (days, samples)
- Test metrics (RMSE, MAE, MAPE, R²)
- Predictions vs actuals
- All data for visualization

---

## 📈 Results & Analysis

### Experiments Run

```
Total Experiments = Symbols × Window Sizes × Models
                  = 5 × 2 × 5
                  = 50 experiments per dataset
                  = 100 total (raw + with_indicators)
```

### Output Files

1. **CSV Results**:
   - `rolling_window_results_raw_YYYYMMDD_HHMMSS.csv`
   - `rolling_window_results_with_indicators_YYYYMMDD_HHMMSS.csv`

2. **Visualizations**:
   - Train-test split plots per symbol
   - Rolling window mechanism illustrations
   - Forecast results with actuals vs predictions

### Analysis Provided

- Best models by RMSE
- Performance by symbol
- Performance by window size
- Performance by model type
- Detailed metrics comparison

---

## ✅ Data Leakage Prevention Checklist

### Training Phase
- [x] Test data completely excluded from training
- [x] Rolling window only on training data
- [x] No future values in any training sample
- [x] Scaler fitted only on training data

### Testing Phase
- [x] Initial window from training data end
- [x] Recursive forecasting uses predictions only
- [x] No actual test values leaked into predictions
- [x] Temporal order strictly maintained

### Verification
- [x] Visual confirmation via plots
- [x] Date range checks in code
- [x] Split index verification
- [x] Manual inspection possible

---

## 🎓 Key Concepts

### Why Rolling Window?

**Advantages:**
1. **More training samples**: From N days → (N - window_size) samples
2. **Temporal patterns**: Learns relationships in time
3. **Flexibility**: Different window sizes capture different patterns
4. **Realistic**: Mirrors how forecasting works in practice

### Why 30-Day Test Split?

**Rationale:**
1. **Sufficient evaluation**: 30 days = ~1 month of trading
2. **Realistic scenario**: Common forecasting horizon
3. **Simple verification**: Clear boundary, easy to check
4. **Robust training**: 9+ years = extensive historical learning

### Why Recursive Forecasting?

**Importance:**
1. **Real-world simulation**: How actual forecasting works
2. **Error accumulation**: Tests model robustness
3. **No cheating**: Can't use future actual values
4. **Challenging**: More difficult but honest evaluation

---

## 🔧 Usage Instructions

### 1. Run Cells in Order

```python
# Cell 1-4: Setup & Configuration
# Cell 5-7: Data Loading & Cleaning
# Cell 8-9: Train-Test Split Visualization
# Cell 10-12: Rolling Window Visualization
# Cell 13-14: Training Functions
# Cell 15: Demo Training
# Cell 16-18: Full Training Pipeline
# Cell 19-21: Results Analysis
```

### 2. Verify No Data Leakage

After running split visualization:
- Check train date range ends before test begins
- Verify no date overlap
- Confirm test period is exactly 30 days
- Review statistics printout

### 3. Modify Configuration

```python
# Change window sizes
WINDOW_SIZES = [7, 14, 21, 30]

# Change test period
SPLIT_CONFIG = {
    'test_days': 60,  # Test on last 60 days instead
}

# Change models
ML_MODELS = {
    "LinearRegression": LinearRegression(),
    # Add more models...
}
```

---

## 📚 References & Theory

### Time Series Cross-Validation
- Traditional CV doesn't work for time series (data leakage!)
- Need temporal ordering
- Test must be after train

### Rolling Window
- Also called "sliding window"
- Creates multiple training samples
- Each sample is a temporal sequence

### Recursive Forecasting
- Also called "multi-step ahead forecasting"
- Iterative prediction
- Uses previous predictions as inputs

---

## 🆚 Comparison with Walk Forward Validation

| Aspect | Walk Forward CV | Rolling Window (This Notebook) |
|--------|----------------|-------------------------------|
| **Complexity** | Higher | Lower |
| **Test Splits** | Multiple | Single (30 days) |
| **Training Data** | Varies per fold | Fixed (9+ years) |
| **Interpretability** | Complex | Simple & Clear |
| **Leakage Risk** | Moderate (needs care) | Minimal (straightforward) |
| **Use Case** | Research, robustness | Production, realistic forecast |

---

## 💡 Tips & Best Practices

### 1. Always Visualize Your Splits
```python
# ALWAYS run visualization before training
visualize_train_test_split(data, dates, split_index, symbol)
```

### 2. Verify Split Logic
```python
# Print and check
print(f"Train: {train_dates[0]} to {train_dates[-1]}")
print(f"Test:  {test_dates[0]} to {test_dates[-1]}")
assert train_dates[-1] < test_dates[0]  # No overlap!
```

### 3. Monitor Recursive Predictions
```python
# Compare predictions vs actuals
plt.plot(test_dates, actuals, label='Actual')
plt.plot(test_dates, predictions, label='Predicted')
```

### 4. Check for Data Leakage Signs
```python
# If R² is suspiciously high (>0.99), investigate!
# Perfect predictions usually indicate leakage
```

---

## 🐛 Common Pitfalls (AVOIDED)

### ❌ Don't Do This:
```python
# WRONG: Using all data to create sequences
X, y = create_sequences(all_data, window_size)
train_size = int(0.8 * len(X))
X_train, X_test = X[:train_size], X[train_size:]
# Problem: Test windows contain training data!
```

### ✅ Do This Instead:
```python
# CORRECT: Split first, then create sequences
train_data, test_data = split(all_data)
X_train, y_train = create_sequences(train_data, window_size)
# No leakage: test_data never used in training
```

---

## 📞 Questions & Debugging

### Q: How do I know there's no data leakage?

**A: Multiple verification methods:**
1. Visual inspection of split plots
2. Date range checks in output
3. Code review (split logic)
4. Result sanity checks (not too perfect)

### Q: Why recursive forecasting instead of direct?

**A: Realism:**
- In production, you only have past data
- Can't use actual future values
- Must use predictions as inputs

### Q: Can I change the test period?

**A: Yes!**
```python
SPLIT_CONFIG = {
    'test_days': 60,  # Test on 60 days
}
```

---

## 🎉 Success Metrics

After running this notebook, you should have:

- [x] Clean train-test split with verification
- [x] Visual proof of no data leakage
- [x] Rolling window sequences properly created
- [x] Recursive forecasts for realistic evaluation
- [x] Comprehensive results for all combinations
- [x] Clear documentation of methodology
- [x] Reproducible pipeline

---

## 📖 Conclusion

This refactored notebook provides a **simple, clear, and leak-proof** approach to time series forecasting:

1. **Clean Split**: Train on 9+ years, test on 30 days
2. **Rolling Window**: Creates sequences from training data only
3. **Recursive Forecast**: Realistic multi-step predictions
4. **Visual Verification**: Plots confirm no leakage
5. **Comprehensive Results**: All metrics and comparisons

**Most Importantly:** The approach is easy to understand, verify, and trust!

---

*Generated for: Financial News Sentiment - Machine Learning Module*  
*Date: 2025*  
*Method: Rolling Window with No Data Leakage Guarantee* 🔒
