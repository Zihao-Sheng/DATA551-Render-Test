# Reflection (Milestone 2)

So far, we have implemented a working Dash + Altair dashboard with coordinated views for Spotify track exploration. Users can filter data by keyword, genre, explicit flag, tempo range, and popularity range. The main scatter plot (Energy vs Valence) supports both brush selection and pan/zoom interaction. Selections are propagated to linked views, including a genre summary chart, an average audio profile chart, a feature density chart, and a sortable/paginated track list.

We also implemented a "Discover Similar Tracks" panel. Users can select a reference song and retrieve audio-similar tracks with lower popularity. Similarity is computed from normalized audio features. The genre selector has been upgraded to a searchable dropdown with removable selected chips for better usability on large category sets.

What is not yet implemented:
1. Compare Mode is currently a placeholder panel only. The full workflow (adding comparison groups, side-by-side comparison state, and dedicated interactions) is planned but not yet functional.
2. Mark song as liked is not yet implemented. We currently do not have a persistent liked-songs action/state in the track list or similar-tracks panel.

Known issues and limitations:
1. In genre-related visualizations, when too many categories are displayed, x-axis labels can overlap and reduce readability.
2. On free deployment instances, some cards occasionally fail to render. Our current hypothesis is that the combination of dataset size and multiple Altair charts can exceed free-instance resource limits.
3. Performance may degrade under broad filters because multiple linked charts update simultaneously.

What the dashboard does well:
1. It provides a clear exploration path from overview (scatter) to detailed inspection (table and similar tracks).
2. It supports linked interactivity across views, making exploratory analysis more efficient than static charts.
3. It has practical filtering controls that allow users to quickly narrow the catalog.

Future improvements:
1. Fully implement Compare Mode interactions and state management.
2. Add a complete "mark as liked" workflow with persistent state and user-facing feedback.
3. Improve rendering stability on free cloud tiers by using a reduced/optimized dataset and lighter chart rendering.
4. Improve readability for dense category plots through dynamic top-N display and smarter label handling.
