# Reflection (Milestone 4)

## What Has Been Implemented

The Spotify Track Insights Explorer is now a functional multi-view dashboard. Core views are implemented and linked, including an energy vs valence scatter plot with brush and point selection, a genre summary bar chart, a feature density chart, and togglable tempo distribution and mood quadrant panels. Selecting a track opens an audio profile radar chart, and a compare toggle lets users lock a primary track and overlay a second track for direct comparison.

A similar tracks panel recommends audio-similar tracks with lower popularity to support playlist discovery. The liked tracks/star system, listed as unfinished in Milestone 2, has now been fully implemented, allowing users to star tracks and filter to favourites.

Following TA feedback, each feature card now includes a collapsible '?' helper button explaining chart purpose and interaction logic. A Safe Mode per-genre downsampling mechanism was also introduced to keep deployment stable on Render's free tier and maintain responsiveness.

## What Was Not Implemented and Why

Group vs group compare mode was proposed in the original plan but was not implemented. It would require two independent filter states and side-by-side distributions. Maintaining both states would significantly increase callback complexity and memory usage, hurting performance on our Render deployment. The single-track radar comparison covers the most common inspection workflow with lower complexity.

Spotify live integration was the most frequently requested feature in peer feedback. While technically feasible through the Spotify Web API, it requires OAuth authentication and rate-limit management that are difficult to support in a stateless Dash app on a free hosting tier. Also, the dataset is from 2022, so some track IDs may no longer be valid on the live platform.

Track export (CSV download) from the original proposal was also deprioritized in favor of higher-impact usability improvements identified during Milestone 3 feedback.

## Response to Peer and TA Feedback

Peer feedback from Milestone 3 highlighted three themes. First, several reviewers found the "total / filtered / selected" counters and the relationship between brush selection and filtering unclear. To address this, we added collapsible helper explanations to each feature card.

Second, users reported needing to scroll too far to access the track list. We reorganised the layout and introduced a tab-based panel system to reduce vertical scrolling.

Third, reviewers requested richer per-track information and comparison features. This feedback motivated the track profile radar chart and Compare overlay.

One known limitation is that Safe Mode downsampling may slightly approximate feature distributions for larger genres, because only up to 100 tracks per genre are retained. This may marginally affect density chart shapes for high-volume genres, but keeps the dashboard responsive within deployment constraints.

Overall, feedback confirmed that the core exploration workflow of filter, scatter, inspect, discover is intuitive and effective. The main remaining limitation is the lack of live Spotify connectivity, which would improve interactivity but remains outside the technical scope of this project.
