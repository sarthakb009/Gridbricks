from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo
import os
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

API_BASE = os.getenv('ELEXON_API_BASE', 'https://data.elexon.co.uk/bmrs/api/v1')
app = FastAPI(title='Northstar Wind Desk API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

def parse_utc(value: str) -> datetime:
    normalized = value.replace('Z', '+00:00').replace(' ', 'T')
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


async def fetch_dataset(code: str, params: dict[str, Any]):
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.get(f'{API_BASE}/datasets/{code}/stream', params=params)
        response.raise_for_status()
        body = response.json()
        return body.get('data', body) if isinstance(body, dict) else body

@app.get('/api/health')
def health(): return {'status': 'ok', 'source': 'Elexon Insights API', 'datasets': ['FUELHH', 'WINDFOR']}

@app.get('/api/wind')
async def wind(day: date = Query(...), decision_time: str = Query('10:00'), timezone_name: str = Query('Europe/London')):
    """Return day-ahead decision vintage and actual outturn for a delivery day."""
    if day.year != 2026 or day.month != 1:
        raise HTTPException(status_code=400, detail='This prototype is scoped to January 2026 delivery dates.')
    try:
        zone = ZoneInfo(timezone_name)
        hh, mm = map(int, decision_time.split(':'))
        cutoff_local = datetime.combine(day - timedelta(days=1), time(hh, mm), zone)
        cutoff = cutoff_local.astimezone(timezone.utc)
        start = datetime.combine(day, time.min, timezone.utc)
        end = start + timedelta(days=1)
        def z(value): return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        actuals, forecasts = await __import__('asyncio').gather(
            fetch_dataset('FUELHH', {'fuelType':'WIND', 'publishDateTimeFrom':z(start), 'publishDateTimeTo':z(end+timedelta(days=1)), 'format':'json'}),
            fetch_dataset('WINDFOR', {'publishDateTimeFrom':z(cutoff-timedelta(days=4)), 'publishDateTimeTo':z(cutoff), 'format':'json'})
        )
        actual_by_start = {}
        for row in actuals:
            target = row.get('startTime')
            if row.get('fuelType') == 'WIND' and target and row.get('generation') is not None:
                target_time = parse_utc(target)
                if start <= target_time < end:
                    actual_by_start[target_time.isoformat()] = float(row['generation'])
        # Select the latest forecast publication at or before the day-ahead cutoff per settlement period.
        chosen = {}
        for row in forecasts:
            target, published = row.get('startTime'), row.get('publishTime')
            if not target or not published or row.get('generation') is None: continue
            target_time = parse_utc(target)
            if not start <= target_time < end: continue
            pub = parse_utc(published)
            if pub > cutoff: continue
            key = target_time.isoformat()
            if key not in chosen or pub > chosen[key]['_published']:
                chosen[key] = {'startTime': target_time, 'forecast': float(row['generation']), '_published': pub}
        points=[]
        for target, row in sorted(chosen.items()):
            actual = actual_by_start.get(target)
            local = row['startTime'].astimezone(zone)
            points.append({'startTime':row['startTime'].isoformat().replace('+00:00','Z'), 'localTime':local.strftime('%H:%M'), 'forecast':row['forecast'], 'actual':actual, 'publishTime':row['_published'].isoformat().replace('+00:00','Z'), 'error': (row['forecast']-actual) if actual is not None else None})
        valid = [p for p in points if p['actual'] is not None]
        if not points: raise HTTPException(status_code=404, detail='No WINDFOR forecasts found before this decision cutoff. Try another cutoff or date.')
        errors = [p['forecast']-p['actual'] for p in valid]
        mae = sum(abs(x) for x in errors)/len(errors) if errors else None
        rmse = (sum(x*x for x in errors)/len(errors))**0.5 if errors else None
        actual_sum = sum(p['actual'] for p in valid)
        wape = sum(abs(x) for x in errors)/actual_sum*100 if actual_sum else None
        return {'deliveryDate':day.isoformat(), 'decisionCutoff':cutoff.isoformat().replace('+00:00','Z'), 'timezone':timezone_name, 'forecastVintage':max(p['publishTime'] for p in points), 'periodCount':len(points), 'matchedPeriodCount':len(valid), 'metrics':{'mae':mae,'rmse':rmse,'wape':wape,'bias':sum(errors)/len(errors) if errors else None}, 'points':points, 'source':'Elexon Insights API', 'datasets':['WINDFOR','FUELHH']}
    except HTTPException: raise
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=502, detail=f'Elexon data request failed: {exc}')
