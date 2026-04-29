CREATE TABLE IF NOT EXISTS iris_to_quartier (
    code_iris VARCHAR(16) PRIMARY KEY,
    code_insee_quartier VARCHAR(16) NOT NULL,
    insee_com VARCHAR(16),
    INDEX idx_iris_to_quartier_quartier (code_insee_quartier)
);

TRUNCATE TABLE iris_to_quartier;

LOAD DATA LOCAL INFILE 'C:/Users/rayan/Desktop/Projet_architecture_donn-es/data/exports/relational/iris_to_quartier.csv'
INTO TABLE iris_to_quartier
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(code_iris, code_insee_quartier, insee_com);
