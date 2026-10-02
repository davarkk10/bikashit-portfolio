-- Q1-Q3: How often are orders late, and what does lateness do to the review score?
SET search_path = olist;

-- Q1. Headline: on-time rate and review outcome, late vs on time (delivered orders that have a review)
SELECT CASE WHEN is_late THEN 'late' ELSE 'on time or early' END AS delivery,
       COUNT(*) AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_orders,
       ROUND(AVG(review_score), 2) AS avg_review,
       ROUND(100.0 * AVG((review_score <= 2)::int), 1) AS pct_1_2_star
FROM delivered WHERE review_score IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- Q2. Dose-response: the later the order, the worse the review
SELECT CASE WHEN days_vs_promise <= -7 THEN '1. 7+ days early'
            WHEN days_vs_promise <= 0  THEN '2. 0-6 days early'
            WHEN days_vs_promise <= 3  THEN '3. 1-3 days late'
            WHEN days_vs_promise <= 7  THEN '4. 4-7 days late'
            WHEN days_vs_promise <= 14 THEN '5. 8-14 days late'
            ELSE '6. 15+ days late' END AS bucket,
       COUNT(*) AS orders,
       ROUND(AVG(review_score), 2) AS avg_review,
       ROUND(100.0 * AVG((review_score <= 2)::int), 1) AS pct_1_2_star
FROM delivered WHERE review_score IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- Q3. Monthly trend (full months Jan 2017 - Aug 2018): late rate and bad-review rate move together
SELECT purchase_month,
       COUNT(*) AS delivered_orders,
       ROUND(100.0 * AVG(is_late::int), 1) AS late_pct,
       ROUND(100.0 * AVG((review_score <= 2)::int), 1) AS pct_1_2_star
FROM delivered
WHERE purchase_month BETWEEN '2017-01-01' AND '2018-08-01' AND review_score IS NOT NULL
GROUP BY 1 ORDER BY 1;
