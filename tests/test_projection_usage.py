from text2query.submission.projection_usage import projection_usage


def test_projection_usage_keeps_entity_dimensions_without_transferring_filters_or_metrics():
    steps = [{"engine": "MYSQL", "query": "SELECT LEFT(c.area_id,4) AS city, c.name, SUM(o.amount) / 100 AS rate FROM demo.customer c JOIN demo.orders o ON c.id=o.customer_id WHERE c.kind='unrelated' GROUP BY LEFT(c.area_id,4),c.name"}]
    result = projection_usage(steps)
    assert result[0]["nonaggregate_output_dimensions"] == ["LEFT(c.area_id, 4) AS city", "c.name"]
    assert result[0]["group_by"] == ["LEFT(c.area_id, 4)", "c.name"]
    assert "unrelated" not in str(result)
    assert "SUM" not in str(result)
