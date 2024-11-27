	create database bet;

use bet;

create table usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    data_nascimento DATE NOT NULL,
    saldo DECIMAL(10, 2) DEFAULT 0.00,
    is_moderator BOOLEAN DEFAULT FALSE
);

select*from usuarios;

create table eventos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(50) NOT NULL,
    descricao VARCHAR(150) NOT NULL,
    valor_cota DECIMAL(10, 2) NOT NULL,
    data_evento DATE NOT NULL,
    inicio_apostas DATETIME NOT NULL,
    fim_apostas DATETIME NOT NULL,
    criador_id INT NOT NULL,
    status ENUM('aguardando_aprovacao', 'aprovado', 'reprovado', 'finalizado') DEFAULT 'aguardando_aprovacao',
    FOREIGN KEY (criador_id) REFERENCES usuarios(id)
);

select*from eventos;

create table apostas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evento_id INT NOT NULL,
    usuario_id INT NOT NULL,
    valor DECIMAL(10, 2) NOT NULL,
    escolha ENUM('Sim', 'Não') NOT NULL,
    data DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evento_id) REFERENCES eventos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

select*from apostas;

CREATE TABLE saques (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    valor_saque DECIMAL(10, 2) NOT NULL,
    taxa DECIMAL(10, 2) NOT NULL,
    banco VARCHAR(50),
    agencia VARCHAR(20),
    conta VARCHAR(20),
    chave_pix VARCHAR(100),
    data_saque DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

create table moderadores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

select*from moderadores;

CREATE INDEX idx_evento_status ON eventos (status);
CREATE INDEX idx_aposta_evento ON apostas (evento_id);
CREATE INDEX idx_usuario_email ON usuarios (email);