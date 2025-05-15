import os
import asyncio
import aiohttp
from aiolimiter import AsyncLimiter
from datetime import datetime, timedelta

# 환경 변수로 API 키 관리
API_KEY = os.getenv("SERPAPI_KEY")
BASE_URL = "https://serpapi.com"

# 초당 5회, 분당 60회 제한 예시
rate_limiter = AsyncLimiter(max_rate=5, time_period=1)

# 단순 캐시 (symbol 쿼리당 60초 TTL)
_cache = {}
CACHE_TTL = timedelta(seconds=60)

async def fetch_json(session, url, params):
    try:
        # 레이트 리밋
        async with rate_limiter:
            # 타임아웃 설정
            timeout = aiohttp.ClientTimeout(total=3)
            async with session.get(url, params=params, timeout=timeout) as resp:
                data = await resp.json()
                if resp.status != 200:
                    code = data.get('code', resp.status)
                    msg = data.get('message', resp.reason)
                    raise Exception(f"API Error {code}: {msg}")
                return data
    except asyncio.TimeoutError:
        raise Exception("요청이 너무 오래 걸렸습니다. 잠시 후 다시 시도해 주세요.")
    except Exception as e:
        raise

async def get_quote(symbol: str):
    now = datetime.utcnow()
    # 캐시 확인
    if symbol in _cache:
        cached_time, cached_data = _cache[symbol]
        if now - cached_time < CACHE_TTL:
            return cached_data

    url = f"{BASE_URL}/finance/quotes/{symbol}"
    params = {'api_key': API_KEY}
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {API_KEY}"}) as session:
        data = await fetch_json(session, url, params)
        # 공통 포맷으로 변환
        result = {
            "source": "finance",
            "symbol": symbol.upper(),
            "price": data.get("price"),
            "time": data.get("time")
        }
        # 캐시에 저장
        _cache[symbol] = (now, result)
        return result

async def handle_user_request(request_text: str):
    # 간단 예시: 'AAPL'만 추출
    symbol = request_text.strip().upper()
    try:
        quote = await get_quote(symbol)
        return f"{quote['symbol']} 현재가: ${quote['price']} (기준 시각: {quote['time']})"
    except Exception as e:
        return str(e)

# 테스트용 실행
if __name__ == '__main__':
    async def main():
        resp = await handle_user_request('AAPL')
        print(resp)
    asyncio.run(main())
