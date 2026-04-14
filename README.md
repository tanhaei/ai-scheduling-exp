# **Revisiting the "Impossible Region": AI in Software Scheduling**

This repository contains the **datasets** and **analysis scripts** for the following research paper:

Title: Revisiting the ``Impossible Region'': An Empirical Study on the Security-Speed Trade-off of Generative Artificial Intelligence in Software Scheduling  
Authors: Mohammad Tanhaei, Roohallah Alizadehsani  
Journal: The Journal of Systems and Software

## **📋 Overview**

Traditional software project scheduling models (most notably the **Putnam model**) postulate that compressing a project schedule below 75% of the nominal time results in an exponential increase in effort or project failure (a theoretical constraint known as the **"Impossible Region"**).

This study empirically investigates whether Generative AI tools (such as GitHub Copilot and GPT-4) can challenge these decades-old assumptions in a controlled micro-level programming task. By conducting a controlled experiment with **48 professional software developers**, the manuscript reports that AI-assisted teams can more often deliver acceptable software within the traditional impossible region. The exploratory analysis in the paper also reports a substantially smaller AI-assisted time-sensitivity exponent, with **$\hat{\alpha}_{AI} \approx 0.21$** and a wide bootstrap confidence interval.

## **📂 Repository Structure**

The file structure is organized as follows:

```
git/  
├── data/  
│   └── dataset\_48.csv       \# Raw experimental data (48 participants)  
├── scripts/  
│   ├── data.py              \# Script for data preprocessing and figure generation  
│   └── analysis.R           \# R script for exploratory alpha estimation and sensitivity plotting  
└── requirements.txt         \# List of Python dependencies
```

### **File Descriptions**

* **data/dataset_48.csv**: Contains metrics collected from the 48 participants. Key columns include:  
  * Group: Experimental group (G1 to G4)  
  * Effort\_Hours: Effort exerted (Person-Hours)  
  * Quality\_Score: Composite quality score (0 to 100)  
  * Success: Submission outcome flag used in the repository analysis  
* **scripts/data.py**: Python script used for loading the dataset and generating manuscript figures for observed effort, quality distribution, and the illustrative theoretical curve.  
* **scripts/analysis.R**: R script for reproducing the manuscript-referenced exploratory AI time-sensitivity estimate and the corresponding sensitivity figure.

## **🚀 Usage**

### **Prerequisites**

You will need **Python 3.9+** and **R** installed. First, install the required Python libraries:

```
pip install -r requirements.txt
```

### **Running the Analysis**

1. Data Preprocessing and Figures:  
   Run the Python script to generate the manuscript figures:  
   `python scripts/data.py`

2. Exploratory Alpha Estimation:  
   Run the R script to generate the sensitivity results and manuscript-aligned outputs:  
   `Rscript scripts/analysis.R`

## **📊 Key Findings**

Based on the empirical analysis:

* **Success Rate:** AI-assisted teams achieved a **92%** success rate under compressed schedule conditions (compared to **0%** for traditional teams).  
* **Effort Pattern:** The manuscript reports a markedly flatter AI-assisted effort response under schedule compression in this bounded task.  
* **Security Trade-off:** While development speed increased, AI-generated code exhibited a higher rate of high-severity security findings (**28%** vs. **9%**), underscoring the need for rigorous automated security auditing.

## **📝 Citation**

If you use this dataset or code in your research, please cite the associated manuscript:

## **⚖️ License**

This project is licensed under the **MIT License**. You are free to use the data with appropriate attribution.
