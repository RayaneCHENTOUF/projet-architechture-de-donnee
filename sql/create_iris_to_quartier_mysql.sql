CREATE TABLE IF NOT EXISTS iris_to_quartier (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code_iris VARCHAR(16) NOT NULL,
    code_insee_quartier VARCHAR(16) NOT NULL,
    nom_quartier VARCHAR(100),
    insee_com VARCHAR(16),
    arrondissement VARCHAR(2),
    nom_iris VARCHAR(100),
    INDEX idx_iris_code (code_iris),
    INDEX idx_quartier_code (code_insee_quartier),
    INDEX idx_arrondissement (arrondissement)
);

TRUNCATE TABLE iris_to_quartier;

LOAD DATA LOCAL INFILE 'C:/Users/33601/Desktop/Projet_architecture_Finale/data/exports/relational/iris_to_quartier.csv'
INTO TABLE iris_to_quartier
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(code_iris, code_insee_quartier, nom_quartier, insee_com, arrondissement, nom_iris);
