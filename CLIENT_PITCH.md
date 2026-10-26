# Northstar Wind Desk — client walkthrough

## The pitch

**Make the wind forecast you bought against visible.** Northstar shows the latest Elexon wind forecast that was available by the desk's chosen day-ahead cutoff, lines it up with the actual half-hourly outturn, and quantifies how far the forecast missed. Buyers can use that evidence to frame residual procurement decisions with a known forecast uncertainty, rather than relying on a forecast that may have been revised after the decision.

## Five-minute demo

1. **Set the decision.** Choose a January 2026 delivery day and the desk's UK-time decision cutoff.
2. **Freeze the view.** Point out the selected forecast publication time. Each settlement period uses the newest forecast published no later than the cutoff.
3. **Read the shape.** Compare day-ahead wind against actual outturn and inspect the signed half-hourly misses.
4. **Quantify uncertainty.** MAE answers “how big is a typical miss?”; WAPE scales total absolute miss to delivered wind volume; bias shows systematic over- or under-forecasting.
5. **Take the evidence away.** Export all periods and publication timestamps to CSV for desk review.

## Scope and next step

This first release deliberately uses only national Elexon WINDFOR and FUELHH data for January 2026. It makes forecast uncertainty legible; it does not calculate a client's net position or a recommended purchase volume because demand, contracted generation, portfolio position, and price inputs are outside this data scope. Agree the real auction decision cutoff with the desk, then connect the client's demand and portfolio position to turn wind forecast uncertainty into a net procurement view.
