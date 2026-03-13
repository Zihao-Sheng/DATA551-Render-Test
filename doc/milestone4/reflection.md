# Reflection (Milestone 4)

## What Has Been Implemented

The Spotify Track Insights Explorer is a fully functional multi-view dashboard at this point. All core views are implemented and linked, including an energy vs valence scatter plot with brush and point selection, a genre summary bar chart, a feature density chart, and togglable tempo distribution and mood quadrant panels. Selecting a track opens an audio profile radar chart, and a compare toggle allows users to lock a primary track and overlay a second track for direct audio-feature comparison.

A similar tracks panel recommends audio-similar tracks with lower popularity to support playlist discovery and curation. The liked tracks/star system, listed as unfinished in the Milestone 2 reflection, has now been fully implemented, allowing users to star tracks and filter to favourites.

Following TA feedback, each feature card now includes a collapsible '?' helper button explaining the chart's purpose and interaction logic. A Safe Mode per-genre downsampling mechanism was also introduced to ensure stable deployment on Render's free tier and keep the dashboard responsive with larger datasets.

## What Was Not Implemented and Why

Group vs group compare mode was proposed in the original project plan but was not implemented. The feature would allow users to define two independent filter states and compare their feature distributions side by side. Maintaining two simultaneous filter states would significantly increase callback complexity and memory usage, which would negatively impact performance on our Render deployment. The single-track radar comparison already supports the most common inspection workflow with much lower complexity.

Spotify live integration was the most frequently requested feature in peer feedback. While technically feasible through the Spotify web API, it requires OAuth authentication and rate limit management that are difficult to support in a stateless Dash application deployed on a free hosting tier. Additionally, the dataset dates from 2022, meaning some track ids may no longer be valid on the live platform.

Track export (CSV download) from the original proposal was also deprioritised in favour of addressing higher-impact usability improvements identified during Milestone 3 feedback.

## Response to Peer and TA Feedback

Peer feedback from Milestone 3 highlighted three main themes. First, several reviewers found the "total / filtered / selected" counters and the relationship between brush selection and filtering unclear. To address this, we added collapsible helper explanations to each feature card.

Second, users reported needing to scroll too far to access the track list. We reorganised the layout and introduced a tab-based panel system to reduce vertical scrolling.

Third, reviewers requested richer per-track information and comparison features. This feedback motivated the track profile radar chart and the Compare overlay functionality.

One known limitation of the current system is that safe mode downsampling may slightly approximate feature distributions for larger genres, as only up to 100 tracks per genre are retained. This may marginally affect density chart shapes for high-volume genres. However, this tradeoff allows the dashboard to remain responsive within the deployment constraints.

Overall, feedback confirmed that the core exploration workflow of filter, scatter, inspect, discover is intuitive and effective. The main remaining limitation is the lack of live Spotify connectivity, which would improve interactivity but remains outside the technical scope of this project.
