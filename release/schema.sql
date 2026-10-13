-- MCP ecosystem schema — generated from the live models (exported tables only).
-- Resume-marker tables are omitted; they are crawl bookkeeping, not data.

CREATE TABLE mcp_registries (
	registry_id UUID NOT NULL, 
	registry_name VARCHAR(100), 
	url VARCHAR(255), 
	PRIMARY KEY (registry_id)
);

CREATE TABLE mcp_servers (
	server_id UUID NOT NULL, 
	repository_url VARCHAR(255), 
	website_url VARCHAR(255), 
	server_name VARCHAR(100) NOT NULL, 
	canonical_name VARCHAR(200), 
	primary_language VARCHAR(50), 
	stars_count INTEGER, 
	discovery_source VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	last_updated TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (server_id), 
	UNIQUE (repository_url)
);

CREATE TABLE server_registry_listings (
	listing_id UUID NOT NULL, 
	server_id UUID, 
	registry_id UUID, 
	listed_as_name VARCHAR(255), 
	listing_url VARCHAR(500), 
	listing_metadata JSONB, 
	discovered_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (listing_id), 
	UNIQUE (server_id, registry_id), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id) ON DELETE CASCADE, 
	FOREIGN KEY(registry_id) REFERENCES mcp_registries (registry_id) ON DELETE CASCADE
);

CREATE TABLE mcp_server_transports (
	transport_id UUID NOT NULL, 
	server_id UUID, 
	transport_type VARCHAR(50) NOT NULL, 
	endpoint_url VARCHAR(255), 
	package_registry VARCHAR(50), 
	package_identifier VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (transport_id), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id) ON DELETE CASCADE
);

CREATE TABLE mcp_tools (
	tool_id UUID NOT NULL, 
	server_id UUID, 
	tool_name VARCHAR(100) NOT NULL, 
	original_description TEXT, 
	input_json_schema JSONB, 
	output_json_schema JSONB, 
	source VARCHAR(20) DEFAULT 'probe' NOT NULL, 
	tdqs_grade VARCHAR(2), 
	discovered_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (tool_id), 
	UNIQUE (server_id, tool_name, source), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id)
);

CREATE TABLE mcp_resources (
	resource_id UUID NOT NULL, 
	server_id UUID, 
	resource_uri_template VARCHAR(255), 
	resource_name VARCHAR(100), 
	description TEXT, 
	mime_type VARCHAR(50), 
	source VARCHAR(20) DEFAULT 'probe' NOT NULL, 
	discovered_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (resource_id), 
	UNIQUE (server_id, resource_uri_template, source), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id)
);

CREATE TABLE mcp_prompts (
	prompt_id UUID NOT NULL, 
	server_id UUID, 
	prompt_name VARCHAR(100) NOT NULL, 
	description TEXT, 
	arguments_json JSONB, 
	source VARCHAR(20) DEFAULT 'probe' NOT NULL, 
	discovered_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (prompt_id), 
	UNIQUE (server_id, prompt_name, source), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id)
);

CREATE TABLE server_dependencies (
	dependency_id UUID NOT NULL, 
	server_id UUID, 
	dependency_name VARCHAR(100), 
	version_constraint VARCHAR(200), 
	dependency_type VARCHAR(20), 
	PRIMARY KEY (dependency_id), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id)
);

CREATE TABLE consumer_repos (
	repo_id BIGSERIAL NOT NULL, 
	owner_login VARCHAR(100), 
	repo_name VARCHAR(100), 
	repository_url VARCHAR(255) NOT NULL, 
	primary_language VARCHAR(50), 
	stars_count INTEGER, 
	discovery_source VARCHAR(20), 
	consumer_type VARCHAR(20), 
	is_also_server BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	last_updated TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (repo_id), 
	UNIQUE (repository_url)
);

CREATE TABLE repo_discovery_signals (
	id UUID NOT NULL, 
	repo_id BIGINT, 
	signal VARCHAR(255), 
	source VARCHAR(20), 
	category VARCHAR(30), 
	discovered_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (repo_id, signal), 
	FOREIGN KEY(repo_id) REFERENCES consumer_repos (repo_id)
);

CREATE TABLE repo_server_usage (
	usage_id UUID NOT NULL, 
	repo_id BIGINT, 
	server_id UUID, 
	raw_server_name VARCHAR(100), 
	config_file_path VARCHAR(255), 
	client_type VARCHAR(30), 
	raw_command VARCHAR(100), 
	raw_args JSONB, 
	match_method VARCHAR(20), 
	discovered_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (usage_id), 
	UNIQUE (repo_id, raw_server_name, config_file_path), 
	FOREIGN KEY(repo_id) REFERENCES consumer_repos (repo_id), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id)
);

CREATE TABLE commits (
	commit_hash VARCHAR(40) NOT NULL, 
	repository_url VARCHAR(255), 
	author_login VARCHAR(100), 
	author_email VARCHAR(255), 
	commit_message TEXT, 
	files_changed INTEGER, 
	lines_additions INTEGER, 
	lines_deletions INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (commit_hash)
);

CREATE TABLE server_pull_requests (
	pr_id BIGSERIAL NOT NULL, 
	server_id UUID, 
	pr_url VARCHAR(255), 
	author_login VARCHAR(100), 
	is_bot_author BOOLEAN, 
	title VARCHAR(255) NOT NULL, 
	body_text TEXT, 
	state VARCHAR(20), 
	destination_branch VARCHAR(100), 
	source_branch VARCHAR(100), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	closed_at TIMESTAMP WITHOUT TIME ZONE, 
	merged_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (pr_id), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id)
);

CREATE TABLE client_pull_requests (
	pr_id BIGSERIAL NOT NULL, 
	repo_id BIGINT, 
	pr_url VARCHAR(255), 
	author_login VARCHAR(100), 
	is_bot_author BOOLEAN, 
	relevance_signal VARCHAR(150), 
	title VARCHAR(255) NOT NULL, 
	body_text TEXT, 
	state VARCHAR(20), 
	destination_branch VARCHAR(100), 
	source_branch VARCHAR(100), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	closed_at TIMESTAMP WITHOUT TIME ZONE, 
	merged_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (pr_id), 
	FOREIGN KEY(repo_id) REFERENCES consumer_repos (repo_id)
);

CREATE TABLE pr_reviews (
	review_id BIGSERIAL NOT NULL, 
	pr_id BIGINT, 
	reviewer_login VARCHAR(100), 
	is_bot_reviewer BOOLEAN, 
	review_state VARCHAR(20), 
	feedback_text TEXT, 
	submitted_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (review_id)
);

CREATE TABLE pr_review_comments (
	comment_id BIGSERIAL NOT NULL, 
	review_id BIGINT, 
	pr_id BIGINT, 
	author_login VARCHAR(100), 
	is_bot_author BOOLEAN, 
	file_path VARCHAR(255), 
	diff_hunk TEXT, 
	comment_text TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (comment_id), 
	FOREIGN KEY(review_id) REFERENCES pr_reviews (review_id)
);

CREATE TABLE pr_commit_bridge (
	pr_id BIGINT NOT NULL, 
	commit_hash VARCHAR(40) NOT NULL, 
	PRIMARY KEY (pr_id, commit_hash)
);

CREATE TABLE ecosystem_issues (
	issue_id BIGSERIAL NOT NULL, 
	server_id UUID, 
	repo_id BIGINT, 
	author_login VARCHAR(100), 
	is_bot_author BOOLEAN, 
	platform VARCHAR(50), 
	source_url VARCHAR(255), 
	title VARCHAR(255) NOT NULL, 
	body_text TEXT, 
	state VARCHAR(20), 
	comment_count INTEGER, 
	reaction_count INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	closed_at TIMESTAMP WITHOUT TIME ZONE, 
	discovered_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (issue_id), 
	FOREIGN KEY(server_id) REFERENCES mcp_servers (server_id), 
	FOREIGN KEY(repo_id) REFERENCES consumer_repos (repo_id)
);

CREATE TABLE issue_comments (
	comment_id BIGSERIAL NOT NULL, 
	issue_id BIGINT, 
	author_login VARCHAR(100), 
	is_bot_author BOOLEAN, 
	comment_text TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (comment_id), 
	FOREIGN KEY(issue_id) REFERENCES ecosystem_issues (issue_id)
);
