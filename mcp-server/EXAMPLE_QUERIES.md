# Example DAX Queries for Azure Analysis Services

This document provides example DAX queries you can use to test and interact with your Azure Analysis Services model.

## Basic Queries

### List All Tables

```dax
-- Get information about all tables in the model
EVALUATE INFO.TABLES()
```

### List All Columns in a Table

```dax
-- Replace 'Sales' with your table name
EVALUATE INFO.COLUMNS('Sales')
```

### Get Top N Rows

```dax
-- Get first 10 rows from a table
EVALUATE TOPN(10, 'Product')

-- Get top 10 products by sales amount
EVALUATE 
TOPN(
    10,
    'Product',
    [Total Sales],
    DESC
)
```

### Get Distinct Values

```dax
-- Get all unique categories
EVALUATE VALUES('Product'[Category])

-- Get distinct customer cities
EVALUATE VALUES('Customer'[City])
```

## Filtering Data

### Simple Filter

```dax
-- Get products where price > 100
EVALUATE 
FILTER(
    'Product',
    'Product'[Price] > 100
)

-- Get sales from 2023
EVALUATE 
FILTER(
    'Sales',
    YEAR('Sales'[OrderDate]) = 2023
)
```

### Multiple Conditions

```dax
-- Products in specific category with price > 50
EVALUATE 
FILTER(
    'Product',
    'Product'[Category] = "Bikes" 
    && 'Product'[Price] > 50
)
```

### Using CALCULATETABLE

```dax
-- More efficient filtering for large datasets
EVALUATE 
CALCULATETABLE(
    'Sales',
    'Product'[Category] = "Accessories",
    'Date'[Year] = 2023
)
```

## Aggregations

### Simple Aggregations

```dax
-- Calculate total sales
EVALUATE 
ROW(
    "Total Sales", SUM('Sales'[Amount]),
    "Avg Sale", AVERAGE('Sales'[Amount]),
    "Max Sale", MAX('Sales'[Amount]),
    "Order Count", COUNTROWS('Sales')
)
```

### Group By / Summarize

```dax
-- Sales by category
EVALUATE 
SUMMARIZECOLUMNS(
    'Product'[Category],
    "Total Sales", SUM('Sales'[Amount]),
    "Order Count", COUNTROWS('Sales')
)

-- Sales by category and year
EVALUATE 
SUMMARIZECOLUMNS(
    'Product'[Category],
    'Date'[Year],
    "Total Sales", SUM('Sales'[Amount]),
    "Avg Price", AVERAGE('Sales'[UnitPrice])
)
```

### Using ADDCOLUMNS

```dax
-- Add calculated columns to results
EVALUATE 
ADDCOLUMNS(
    VALUES('Product'[Category]),
    "Total Sales", CALCULATE(SUM('Sales'[Amount])),
    "Product Count", CALCULATE(COUNTROWS('Product')),
    "Avg Sale", CALCULATE(AVERAGE('Sales'[Amount]))
)
```

## Advanced Queries

### Time Intelligence

```dax
-- Sales by month with year-over-year comparison
EVALUATE 
ADDCOLUMNS(
    SUMMARIZECOLUMNS(
        'Date'[Year],
        'Date'[MonthName],
        "Current Sales", SUM('Sales'[Amount])
    ),
    "Previous Year Sales", CALCULATE(
        SUM('Sales'[Amount]),
        SAMEPERIODLASTYEAR('Date'[Date])
    ),
    "YoY Growth %", 
    DIVIDE(
        SUM('Sales'[Amount]) - CALCULATE(SUM('Sales'[Amount]), SAMEPERIODLASTYEAR('Date'[Date])),
        CALCULATE(SUM('Sales'[Amount]), SAMEPERIODLASTYEAR('Date'[Date]))
    ) * 100
)
```

### Ranking

```dax
-- Top 10 products by sales with ranking
EVALUATE 
TOPN(
    10,
    ADDCOLUMNS(
        VALUES('Product'[ProductName]),
        "Total Sales", CALCULATE(SUM('Sales'[Amount])),
        "Order Count", CALCULATE(COUNTROWS('Sales'))
    ),
    [Total Sales],
    DESC
)
```

### Conditional Aggregation

```dax
-- Sales breakdown by price range
EVALUATE 
ROW(
    "Low Price Sales (<$50)", 
        CALCULATE(
            SUM('Sales'[Amount]),
            'Product'[Price] < 50
        ),
    "Mid Price Sales ($50-$200)", 
        CALCULATE(
            SUM('Sales'[Amount]),
            'Product'[Price] >= 50,
            'Product'[Price] <= 200
        ),
    "High Price Sales (>$200)", 
        CALCULATE(
            SUM('Sales'[Amount]),
            'Product'[Price] > 200
        )
)
```

## Relationships and Lookups

### Using RELATED

```dax
-- Get sales with product details
EVALUATE 
TOPN(
    100,
    SELECTCOLUMNS(
        'Sales',
        "Order ID", 'Sales'[OrderID],
        "Amount", 'Sales'[Amount],
        "Product Name", RELATED('Product'[ProductName]),
        "Category", RELATED('Product'[Category]),
        "Customer Name", RELATED('Customer'[Name])
    )
)
```

### Using RELATEDTABLE

```dax
-- Products with their total sales (from related Sales table)
EVALUATE 
ADDCOLUMNS(
    'Product',
    "Total Sales", SUMX(RELATEDTABLE('Sales'), 'Sales'[Amount]),
    "Order Count", COUNTROWS(RELATEDTABLE('Sales'))
)
```

## Analysis Patterns

### Customer Segmentation

```dax
-- Segment customers by total purchase amount
EVALUATE 
ADDCOLUMNS(
    VALUES('Customer'[CustomerID]),
    "Customer Name", 'Customer'[Name],
    "Total Spent", CALCULATE(SUM('Sales'[Amount])),
    "Order Count", CALCULATE(COUNTROWS('Sales')),
    "Avg Order Value", DIVIDE(
        CALCULATE(SUM('Sales'[Amount])),
        CALCULATE(COUNTROWS('Sales'))
    ),
    "Segment", 
        VAR TotalSpent = CALCULATE(SUM('Sales'[Amount]))
        RETURN
        SWITCH(
            TRUE(),
            TotalSpent > 10000, "VIP",
            TotalSpent > 5000, "Gold",
            TotalSpent > 1000, "Silver",
            "Bronze"
        )
)
ORDER BY [Total Spent] DESC
```

### ABC Analysis (Pareto)

```dax
-- Identify top products contributing to 80% of sales
EVALUATE 
VAR ProductSales = 
    ADDCOLUMNS(
        VALUES('Product'[ProductName]),
        "Sales", CALCULATE(SUM('Sales'[Amount]))
    )
VAR TotalSales = SUMX(ProductSales, [Sales])
VAR RankedProducts = 
    ADDCOLUMNS(
        ProductSales,
        "% of Total", DIVIDE([Sales], TotalSales) * 100,
        "Running Total %", 
            CALCULATE(
                DIVIDE(SUMX(ProductSales, [Sales]), TotalSales) * 100,
                FILTER(
                    ProductSales,
                    [Sales] >= EARLIER([Sales])
                )
            )
    )
RETURN
ADDCOLUMNS(
    RankedProducts,
    "Category", 
        SWITCH(
            TRUE(),
            [Running Total %] <= 80, "A (Top 80%)",
            [Running Total %] <= 95, "B (Next 15%)",
            "C (Bottom 5%)"
        )
)
ORDER BY [Sales] DESC
```

### Cohort Analysis

```dax
-- Customer acquisition by month
EVALUATE 
SUMMARIZECOLUMNS(
    'Date'[Year],
    'Date'[MonthName],
    "New Customers", 
        CALCULATE(
            DISTINCTCOUNT('Sales'[CustomerID]),
            FILTER(
                'Customer',
                'Customer'[FirstPurchaseDate] >= MIN('Date'[Date]) &&
                'Customer'[FirstPurchaseDate] <= MAX('Date'[Date])
            )
        ),
    "Total Customers", DISTINCTCOUNT('Sales'[CustomerID]),
    "Total Sales", SUM('Sales'[Amount])
)
```

## Testing and Validation

### Row Count Check

```dax
-- Count rows in each table
EVALUATE 
UNION(
    ROW("Table", "Sales", "Row Count", COUNTROWS('Sales')),
    ROW("Table", "Product", "Row Count", COUNTROWS('Product')),
    ROW("Table", "Customer", "Row Count", COUNTROWS('Customer')),
    ROW("Table", "Date", "Row Count", COUNTROWS('Date'))
)
```

### Data Quality Checks

```dax
-- Find null or missing values
EVALUATE 
ROW(
    "Sales with NULL Amount", 
        COUNTROWS(FILTER('Sales', ISBLANK('Sales'[Amount]))),
    "Products with NULL Name", 
        COUNTROWS(FILTER('Product', ISBLANK('Product'[ProductName]))),
    "Sales with Invalid Date", 
        COUNTROWS(FILTER('Sales', ISBLANK('Sales'[OrderDate])))
)
```

### Performance Testing

```dax
-- Simple query for performance baseline
EVALUATE 
TOPN(1000, 'Sales')

-- Complex query for stress testing
EVALUATE 
SUMMARIZECOLUMNS(
    'Product'[Category],
    'Product'[SubCategory],
    'Date'[Year],
    'Date'[Quarter],
    'Customer'[Segment],
    "Total Sales", SUM('Sales'[Amount]),
    "Total Cost", SUM('Sales'[Cost]),
    "Profit", SUM('Sales'[Amount]) - SUM('Sales'[Cost]),
    "Margin %", DIVIDE(
        SUM('Sales'[Amount]) - SUM('Sales'[Cost]),
        SUM('Sales'[Amount])
    ) * 100,
    "Order Count", COUNTROWS('Sales'),
    "Unique Customers", DISTINCTCOUNT('Sales'[CustomerID])
)
```

## Tips for Writing DAX

1. **Always use EVALUATE** - Required for standalone queries
2. **Use table names in quotes** - `'Sales'` not `Sales`
3. **Column references use brackets** - `'Sales'[Amount]`
4. **CALCULATE changes filter context** - Essential for dynamic calculations
5. **FILTER vs CALCULATETABLE** - CALCULATETABLE is often more efficient
6. **Use variables (VAR)** - Improves readability and performance
7. **ORDER BY at the end** - For sorted results

## Common Errors

### "The expression refers to multiple columns"
**Fix:** Use VALUES() or DISTINCT() to return a single column

### "A table of multiple values was supplied where a single value was expected"
**Fix:** Wrap aggregation in CALCULATE() or use SUMX/AVERAGEX

### "Column 'X' in table 'Y' cannot be found"
**Fix:** Check spelling and case sensitivity

### "Calculation error in measure"
**Fix:** Use IFERROR() or check for division by zero with DIVIDE()
