---
layout: default
title: "<SITE_TITLE>"
---

<!-- markdownlint-disable MD025 -->

# <SITE_TITLE>

Select an instruction page.

{% assign instruction_pages = site.pages | where_exp: "item", "item.path contains 'Instructions/'" | sort: "path" %}

{% for item in instruction_pages %}
{% if item.lab and item.lab.islab %}

- [{{ item.lab.title }}]({{ item.url | relative_url }}) — {{ item.lab.duration }}

{% endif %}
{% endfor %}
