CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `tempbans` (
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `expires_at` timestamp NOT NULL
);

CREATE TABLE IF NOT EXISTS `log_channels` (
  `server_id` varchar(20) PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS `reputation` (
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `score` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `server_id`)
);

CREATE TABLE IF NOT EXISTS `notes` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `note` varchar(1000) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
);

CREATE TABLE IF NOT EXISTS `evidence` (
  `case_id` int(11) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `url` varchar(500) NOT NULL,
  PRIMARY KEY (`case_id`, `url`)
);

CREATE TABLE IF NOT EXISTS `recovery_snapshots` (
  `server_id` varchar(20) NOT NULL,
  `snapshot_id` varchar(50) NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data` text NOT NULL,
  PRIMARY KEY (`server_id`, `snapshot_id`)
);

CREATE TABLE IF NOT EXISTS `autorole_config` (
  `server_id` varchar(20) PRIMARY KEY,
  `role_id` varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS `user_activity` (
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `message_count` int(11) NOT NULL DEFAULT 0,
  `voice_time` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `server_id`)
);

CREATE TABLE IF NOT EXISTS `quarantine_config` (
  `server_id` varchar(20) PRIMARY KEY,
  `role_id` varchar(20) NOT NULL
);
CREATE TABLE IF NOT EXISTS `staff_members` (
  `server_id` varchar(20) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `position_name` varchar(255),
  PRIMARY KEY (`server_id`, `user_id`)
);

CREATE TABLE IF NOT EXISTS `staff_autorole_config` (
  `server_id` varchar(20) PRIMARY KEY,
  `role_id` varchar(20) NOT NULL,
  `always_apply` boolean NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS `staff_positions` (
  `server_id` varchar(20) NOT NULL,
  `position_name` varchar(255) NOT NULL,
  `role_id` varchar(20),
  `is_custom` boolean NOT NULL DEFAULT 1,
  `rank` INTEGER NOT NULL DEFAULT 999,
  PRIMARY KEY (`server_id`, `position_name`)
);

CREATE TABLE IF NOT EXISTS `stories` (
  `story_id` varchar(20) PRIMARY KEY,
  `server_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `message_id` varchar(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `ticket_panels` (
  `panel_id` varchar(20) PRIMARY KEY,
  `server_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `message_id` varchar(20) NOT NULL,
  `ticket_title` varchar(256),
  `ticket_description` varchar(4000),
  `panel_title` varchar(256),
  `panel_description` varchar(4000),
  `channel_name_format` varchar(256)
);

CREATE TABLE IF NOT EXISTS `ticket_options` (
  `option_id` varchar(20) PRIMARY KEY,
  `panel_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `name` varchar(50) NOT NULL,
  `emoji` varchar(50),
  `category_id` varchar(20) NOT NULL,
  `support_role_id` varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS `tickets` (
  `ticket_id` varchar(20) PRIMARY KEY,
  `server_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `creator_id` varchar(20) NOT NULL,
  `option_id` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'open',
  `claimed_by` varchar(20),
  `panel_id` varchar(20),
  `welcome_msg_id` varchar(20),
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `ticket_buttons` (
  `button_id` varchar(20) PRIMARY KEY,
  `panel_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `label` varchar(50) NOT NULL,
  `emoji` varchar(50),
  `category_id` varchar(20) NOT NULL,
  `support_role_id` varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS `ticket_ping_roles` (
  `server_id` varchar(20) NOT NULL,
  `role_id` varchar(20) NOT NULL,
  PRIMARY KEY (`server_id`, `role_id`)
);

CREATE TABLE IF NOT EXISTS `modmail_config` (
  `server_id` varchar(20) PRIMARY KEY,
  `category_id` varchar(20) NOT NULL,
  `log_channel_id` varchar(20)
);

CREATE TABLE IF NOT EXISTS `modmail_threads` (
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `channel_id` varchar(20) NOT NULL,
  `last_active` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `server_id`)
);

CREATE TABLE IF NOT EXISTS `modmail_blocked` (
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  PRIMARY KEY (`user_id`, `server_id`)
);

CREATE TABLE IF NOT EXISTS `staff_updates_config` (
  `server_id` varchar(20) PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS `staff_strikes` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(500) NOT NULL DEFAULT 'Not specified',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `mod_actions` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `action_type` varchar(50) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_restrictions (server_id varchar(20) NOT NULL, user_id varchar(20) NOT NULL, restriction varchar(50) NOT NULL, PRIMARY KEY (server_id, user_id, restriction));
