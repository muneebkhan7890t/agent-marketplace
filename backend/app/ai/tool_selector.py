def extract_tool(response):

    response = response.strip()

    if "TOOL:" in response:

        return response.replace(
            "TOOL:",
            ""
        ).strip()

    return None