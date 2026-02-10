Create database pick_my_photo;
Use pick_my_photo;

CREATE TABLE admins (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name varchar(50) Not Null,
    phone varchar(12),
    email VARCHAR(150) UNIQUE,
    password VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
select * from admins;

CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role ENUM('admin','studio','client') NOT NULL,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
select * from users;

CREATE TABLE studios (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    studio_name VARCHAR(200) NOT NULL,
    description TEXT,
    city VARCHAR(100),
    address TEXT,
    services VARCHAR(255),
    website VARCHAR(255),
    is_approved TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


CREATE TABLE studio_photos (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT UNSIGNED NOT NULL,
    file_path VARCHAR(300) NOT NULL,
    title VARCHAR(150),
    category VARCHAR(100),
    is_home_photo BOOLEAN DEFAULT FALSE,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (studio_id) REFERENCES studios(id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE subscription_plans (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL(10,2),
    duration_days INT,
    max_galleries INT,
    max_storage_gb INT,
    watermark BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
select * from subscription_plans;
insert into subscription_plans(name, price, duration_days, max_galleries, max_storage_gb, watermark) Value("Advanced Plan", 1499, 28, 20, 80, 0);

CREATE TABLE studio_subscriptions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT NOT NULL,
    plan_id BIGINT NOT NULL,
    start_date DATE,
    end_date DATE,
    status ENUM('active', 'expired', 'cancelled') DEFAULT 'active',
    FOREIGN KEY (studio_id) REFERENCES studios(id),
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);
select * from studio_subscriptions;

CREATE TABLE payments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT,
    plan_id BIGINT,
    razorpay_order_id VARCHAR(100),
    amount DECIMAL(10,2),
    status ENUM('pending','success','failed'),
    instamojo_id VARCHAR(255) default null,
    payment_id VARCHAR(255) default null,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
select * from payments;

CREATE TABLE clients (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (studio_id) REFERENCES studios(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
select * from clients;

CREATE TABLE galleries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT NOT NULL,
    client_id BIGINT NOT NULL,
    title VARCHAR(200),
    password VARCHAR(255),
    is_download_enabled TINYINT(1) DEFAULT 0,
    photos_uploaded TINYINT(1) DEFAULT 0,
    videos_uploaded TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (studio_id) REFERENCES studios(id),
    FOREIGN KEY (client_id) REFERENCES clients(id)
);
select * from galleries;
update galleries set photos_uploaded = 0 where id=4;

update galleries set videos_uploaded = 0 where id=3;

CREATE TABLE gallery_images (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    gallery_id BIGINT NOT NULL,
    image_path VARCHAR(300) NOT NULL,
    is_selected TINYINT(1) DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gallery_id) REFERENCES galleries(id)
);
select * from gallery_images;

CREATE TABLE gallery_videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    gallery_id BIGINT NOT NULL,
    video_path VARCHAR(255) NOT NULL,
    is_selected TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gallery_id) REFERENCES galleries(id) ON DELETE CASCADE
);
select * from gallery_videos;

Update gallery_videos Set  is_selected = 1 where id = 6;

CREATE TABLE photo_selections (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    photo_id BIGINT NOT NULL,
    client_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (photo_id) REFERENCES gallery_images(id),
    FOREIGN KEY (client_id) REFERENCES clients(id),
    UNIQUE(photo_id, client_id)
);
select * from photo_selections;




-- messages for platforms
CREATE TABLE contact_messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150),
    email VARCHAR(150),
    subject VARCHAR(200),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admin_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    admin_id BIGINT,
    action VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE studio_services (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    description VARCHAR(500),
    FOREIGN KEY (studio_id) REFERENCES studios(id) ON DELETE CASCADE
);



CREATE TABLE bookings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT NOT NULL,
    client_id BIGINT NOT NULL,
    booking_date DATE,
    booking_time time,
    status ENUM('pending','confirmed','rejected') DEFAULT 'pending',
    advance_paid int,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp Default current_timestamp,
    FOREIGN KEY (studio_id) REFERENCES studios(id),
    FOREIGN KEY (client_id) REFERENCES users(id)
);
select * from bookings;

CREATE TABLE booking_services (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    booking_id BIGINT NOT NULL,
    service_id BIGINT NOT NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES studio_services(id) ON DELETE CASCADE
);

CREATE TABLE external_bookings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT NOT NULL,
    client_name VARCHAR(150) NOT NULL,
    client_phone VARCHAR(20),
    client_email VARCHAR(150),
    service_name VARCHAR(150) NOT NULL,
    booking_date DATE NOT NULL,
    booking_time TIME NOT NULL,
    price DECIMAL(10,2),
    notes TEXT,
    status ENUM('confirmed','cancelled','completed') DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (studio_id) REFERENCES studios(id) ON DELETE CASCADE
);


CREATE TABLE studio_reviews (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    studio_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL, -- The person giving the review
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (studio_id) REFERENCES studios(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE enquiries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    studio_id INT NOT NULL,
    message TEXT,
    status ENUM('pending', 'replied') DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES users(id),
    FOREIGN KEY (studio_id) REFERENCES studios(id)
);









CREATE TABLE client_face_map (
    id INT AUTO_INCREMENT PRIMARY KEY,
    gallery_id INT NOT NULL,       -- ID of the event/gallery
    image_id INT NOT NULL,         -- Links to your 'gallery_images' table
    azure_person_id VARCHAR(255),  -- The unique ID Microsoft gives this face
    INDEX (gallery_id),
    INDEX (azure_person_id)
);
use pick_my_photo;
select * from client_face_map;
select * from gallery_images;








CREATE TABLE face_map (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_id INT NOT NULL,         -- The ID from your existing gallery_images table
    gallery_id INT NOT NULL,       -- To keep searches inside one specific event
    azure_person_id VARCHAR(255),  -- The ID Microsoft gives us for this person
    INDEX (gallery_id)
);

-- This table stores the link between your local images and Azure's AI IDs
CREATE TABLE face_recognition_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    gallery_id INT NOT NULL,       -- Which event/gallery does this belong to?
    image_id INT NOT NULL,         -- Links to your existing 'gallery_images' table
    azure_person_id VARCHAR(255),  -- The ID Azure gives us for this person
    INDEX (gallery_id),
    INDEX (azure_person_id)
);