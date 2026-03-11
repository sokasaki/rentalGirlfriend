SELECT u.email, r.role_name 
FROM users u 
JOIN roles r ON u.role_id = r.role_id;

SELECT * FROM roles;
