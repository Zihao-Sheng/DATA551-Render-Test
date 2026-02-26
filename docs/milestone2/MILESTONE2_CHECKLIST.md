# Milestone 2 – App Development & Deployment Checklist

- [x] **Repository Structure Organized**  
  Project folder structure follows the recommended layout (`data/`, `src/`, `reports/`, `doc/`, etc.), and files are placed in appropriate directories.

- [x] **Prototype Dashboard Implemented**  
  A working prototype of the dashboard is implemented in Dash + Altair, even if not all planned features are completed.

- [x] **Core Functionality in Place**  
  Most key views and interactions from the proposal are implemented (around ~3 plots with widgets/interactivity).

- [x] **Usable and Self-Documenting Interface**  
  The app has a clear title, meaningful labels for widgets and panes, legends for visual encodings, and is usable in full-screen mode.  

- [x] **Known Limitations and Bugs Identified**  
  Features that are incomplete or not working are clearly identified and documented for TA feedback.

- [x] **Deployment (Heroku / Render) Set Up**  
  The app is successfully deployed and publicly accessible (or deployment platform configured if not using Heroku).

- [ ] **Deployed App Link in README**  
  The public URL of the deployed dashboard is clearly visible near the top of the README.

- [x] **Procfile Configured for src Structure (If Using Heroku)**  
  `Procfile` correctly uses:  
  `web: gunicorn src.app:server`

- [x] **requirements.txt Prepared**  
  `requirements.txt` is created manually with fixed versions for `dash` and `plotly`, and includes `gunicorn`.

- [x] **Early Deployment & Redeployments Completed**  
  Initial deployment done early; app redeployed after major dependency or feature updates.

- [x] **GitHub Issues Created**  
  Issues are used to track planned features, bugs, and incomplete parts of the dashboard.

- [x] **Pull Requests and Reviews Used**  
  Meaningful PRs and code reviews are present in the repo for this milestone (not all commits directly to main).

- [x] **Milestone 2 Reflection Written**  
  `reflection-milestone2.md` is created in the `doc/` folder (≤ 500 words), covering:
  - What is implemented  
  - What is not yet implemented  
  - What is not working  
  - Strengths, limitations, and future improvements

- [ ] **Milestone 2 GitHub Release Created**  
  A GitHub release is created with the name of this milestone, capturing the state of the repo for grading.

- [ ] **Canvas Submission Link Added**  
  The GitHub release link is submitted to Canvas.

- [x] **Optional: README Improved for Users**  
  README includes project motivation, what users can do with the dashboard, and a link to the deployed app.

- [x] **Optional: README Improved for Contributors**  
  README explains how to install dependencies and run the app locally, and how others can contribute.

- [x] **Optional: Visual Preview in README**  
  Add a screenshot or short GIF of the dashboard to quickly show functionality on the GitHub landing page.
