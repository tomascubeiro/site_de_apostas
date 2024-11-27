SELECT * from usuarios;
UPDATE usuarios SET is_moderator = TRUE WHERE email = 'tocubeiro@gmail.com';
SELECT * from eventos;
UPDATE eventos SET status = 'aprovado' WHERE id = 1;