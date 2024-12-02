[![Codecov](https://codecov.io/gh/GuyRoberts1972/st_frame/graph/badge.svg?token=TUTBLEIGR6)](https://codecov.io/gh/GuyRoberts1972/st_frame)
![Pytest](https://github.com/GuyRoberts1972/st_frame/actions/workflows/pytest.yml/badge.svg)
![Pylint](https://github.com/GuyRoberts1972/st_frame/actions/workflows/pylint.yml/badge.svg)
[![CodeQL](https://github.com/GuyRoberts1972/st_frame/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/GuyRoberts1972/st_frame/actions/workflows/github-code-scanning/codeql)

# About
A set of tools for managing and using templated prompt flows across different data sources and models.

# Why
Fun. Privacy. Choice. Customisation. Specific domain and tribal knowledge.

# Features
- Extensible template libray from which flows can be created and customised
- Connectivity to atlasssian JIRA & Confluence (todo: s3, Office, Github)
- Document upload support for common docs (PDF, PPT, DOC, XLS, CSV)
- Prompt flow sessions. Create, duplicate, run reset, export JSON.
- todo: Publish and share flows for others to use via UI or API.

# Key Concepts
Data: Authorised, connected, indexed.
Exploration: Templated processing of data with a selection of models.
Output: Sharable. Publishable.

## Prompt Flow Templates
Definitions of common patterns that bring data sources, user input, LLM models and (todo: actions)
Extensible format for customisation using YAML Actiosn and Anchors and a custom reference key words

## Prompt Flow
An instanciation of a template.
Has a series of steps each with an input, state and an putput.
Create, manage and interact with flows via the UI (todo: and API)

## Connections
Driven through the configuration, allow connection to data sources.

# Main Components
These are published to the GitHub container registry.
Various intallation options.

## Streamlit UI
A UI create and manage flows from templates.

## API
Todo: An API to access and use flows.

# Installation

## Containers
Published in

## Infrastructure as code
Ready to use reference implementations
- todo: CDK scripts to deploy as AWS ECS

## Configuration
Custom configuration covers:
- Prompt Template Library (local, s3 or todo:github)
- State Storage Location (local or s3)
- Connectivity Secrets (atlassian, todo: Office365)
- Model Library - the flavours of LLMs that can be used

Specified at deploy time as a pointer to an AWS SSM param store path.