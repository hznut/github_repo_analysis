SET NAMES utf8;
SET time_zone = '+00:00';
SET foreign_key_checks = 0;
SET sql_mode = 'NO_AUTO_VALUE_ON_ZERO';

SET NAMES utf8mb4;

DROP DATABASE IF EXISTS `repo_analysis`;
CREATE DATABASE `repo_analysis` /*!40100 DEFAULT CHARACTER SET utf8mb4 */;
USE `repo_analysis`;

--DROP TABLE IF EXISTS `committer`;
--CREATE TABLE `committer` (
--  `committer_id` int(11) NOT NULL AUTO_INCREMENT,
--  `email` varchar(100) UNIQUE NOT NULL,
--  PRIMARY KEY (`committer_id`)
--) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


--DROP TABLE IF EXISTS `committer_loc_in_repo`;
--CREATE TABLE `committer_loc_in_repo` (
--  `committer_id` int(11) NOT NULL,
--  `repo_id` int(11) NOT NULL,
--  `loc` int(11) NOT NULL DEFAULT 0,
--  KEY `repo_id` (`repo_id`),
--  KEY `committer_id` (`committer_id`),
--  CONSTRAINT `committer_loc_in_repo_ibfk_1` FOREIGN KEY (`repo_id`) REFERENCES `repo` (`repo_id`),
--  CONSTRAINT `committer_loc_in_repo_ibfk_2` FOREIGN KEY (`committer_id`) REFERENCES `committer` (`committer_id`)
--) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


--DROP TABLE IF EXISTS `repo`;
--CREATE TABLE `repo` (
--  `repo_id` int(11) NOT NULL AUTO_INCREMENT,
--  `repo_url` varchar(10000) UNIQUE NOT NULL,
--  PRIMARY KEY (`repo_id`)
--) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;