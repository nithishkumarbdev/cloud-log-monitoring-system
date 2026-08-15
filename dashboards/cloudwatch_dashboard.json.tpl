{
  "widgets": [
    {
      "type": "metric",
      "x": 0, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "Failed logins over time",
        "region": "${aws_region}",
        "metrics": [["${metric_namespace}", "FailedLoginCount", { "stat": "Sum", "period": 300 }]],
        "view": "timeSeries"
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "Alerts fired (SNS publishes)",
        "region": "${aws_region}",
        "metrics": [["AWS/SNS", "NumberOfMessagesPublished", { "stat": "Sum", "period": 300 }]],
        "view": "timeSeries"
      }
    },
    {
      "type": "log",
      "x": 0, "y": 6, "width": 24, "height": 6,
      "properties": {
        "title": "Log volume by source",
        "region": "${aws_region}",
        "query": "SOURCE '${log_group_name}' | stats count(*) by bin(5m)",
        "view": "table"
      }
    }
  ]
}
