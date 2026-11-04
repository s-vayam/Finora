# Data Quality and Profiling Report — Kaggle Payment Date Dataset

## 1. File Metadata
- **Filename**: `dataset.csv`
- **SHA-256 Hash**: `139482bdc3325a734474d08f48ceee71ab67c84b106f2a0c0fe9479d71be8431`
- **Total Records**: 50,000
- **Total Columns**: 19

## 2. Records and Open/Closed Distribution
- **Closed Invoices (`isOpen=0`)**: 40,000
- **Open Invoices (`isOpen=1`)**: 10,000
- **Clear Date Non-null**: 40,000
- **Clear Date Null**: 10,000

## 3. Entity Counts & Duplicates
- **Unique Customers (`cust_number`)**: 1,099
- **Unique Invoices (`invoice_id`)**: 48,833
- **Exact Duplicate Rows**: 1,161
- **Duplicate Document IDs (`doc_id`)**: 1,161
- **Duplicate Invoice IDs (`invoice_id`)**: 1,166

## 4. Invoice Amount Statistics (`total_open_amount`)
- **Min**: 0.72
- **Max**: 668,593.36
- **Mean**: 32,337.02
- **Median**: 17,609.01
- **Standard Deviation**: 39,205.98
- **Negative Amounts**: 0
- **Zero Amounts**: 0

## 5. Date Ranges
- **Posting Date Range**: 2018-12-30 to 2020-05-22
- **Due Date Range**: 2018-12-24 to 2020-07-10
- **Clear Date Range**: 2019-01-03 to 2020-05-22

## 6. Currency Distribution (Top 10)
- **USD**: 46,081
- **CAD**: 3,919

## 7. Missing Value Summary
- **`clear_date`**: 10,000 missing (20.0%)
- **`area_business`**: 50,000 missing (100.0%)
- **`invoice_id`**: 6 missing (0.01%)
