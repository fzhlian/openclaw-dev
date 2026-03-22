from app.translation import normalize_error_message_to_chinese


def test_normalize_combined_access_gate_and_timeout():
    message = "页面返回访问验证或异常环境页面，未获取到文章正文；The read operation timed out"
    assert (
        normalize_error_message_to_chinese(message)
        == "页面返回访问验证或异常环境页面，未获取到文章正文；网络请求超时"
    )


def test_normalize_http_451():
    assert (
        normalize_error_message_to_chinese("HTTP Error 451: Unavailable For Legal Reasons")
        == "HTTP 451：目标站点因法律限制不可访问"
    )
