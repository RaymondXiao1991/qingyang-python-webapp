-- init database

drop database if exists qingyang;

create database qingyang;

use qingyang;

grant select, insert, update, delete on qingyang.* to 'www-data'@'localhost' identified by 'www-data';

create table users(
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `password` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_time` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_time` (`created_time`),
    primary key (`id`)
)engine=innodb default charset=utf8;

create table blogs(
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `name` varchar(50) not null,
    `summary` varchar(200) not null,
    `content` mediumtext not null,
    `created_time` real not null,
    key `idx_created_time` (`created_time`),
    primary key (`id`)
)engine=innodb default charset=utf8;

create table comments(
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_time` real not null,
    key `idx_created_time` (`created_time`),
    primary key (`id`)
)engine=innodb default charset=utf8;

--把SQL脚本放到MySQL命令行里执行：
--mysql -u root -p < schema.sql

-- email / password: 
-- admin@example.com / password 

insert into users (`id`, `email`, `password`, `admin`, `name`, `image`, `created_time`) values ('0010018336417540987fff4508f43fbaed718e263442526000', 'admin@example.com', '5f4dcc3b5aa765d61d8327deb882cf99', 1, 'Administrator', 'about:blank', 1402909113.628);
