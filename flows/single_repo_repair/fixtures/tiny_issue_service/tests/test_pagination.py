from tiny_issue_service import paginate_issues


def test_first_page_includes_first_item() -> None:
    issues = [f"ISSUE-{index}" for index in range(1, 7)]

    assert paginate_issues(issues, page=1, page_size=2) == ["ISSUE-1", "ISSUE-2"]


def test_second_page_keeps_the_expected_window() -> None:
    issues = [f"ISSUE-{index}" for index in range(1, 7)]

    assert paginate_issues(issues, page=2, page_size=2) == ["ISSUE-3", "ISSUE-4"]
