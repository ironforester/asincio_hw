import asyncio
from datetime import datetime

from aiohttp import ClientSession
from more_itertools import chunked

from models import Session, PersonModel, engine, Base

CHUNK_SIZE = 10
PEOPLE_COUNT = 200


async def async_chunk(async_iter, size):
    buffer_list = []
    while True:
        try:
            item = await async_iter.__anext__()
        except StopAsyncIteration:
            break
        buffer_list.append(item)
        if len(buffer_list) == size:
            yield buffer_list
            buffer_list = []


async def get_url(url, key, session):
    async with session.get(f'{url}') as response:
        data = await response.json()
        return data[key]


async def get_urls(urls, key, session):
    tasks = (asyncio.create_task(get_url(url, key, session)) for url in urls)
    for task in tasks:
        yield await task


async def get_data(urls, key, session):
    result_list = []
    async for item in get_urls(urls, key, session):
        result_list.append(item)
    return ', '.join(result_list)


async def people_insertion(people_chunk):
    async with Session() as session:
        async with ClientSession() as session_deep:
            for person_data in people_chunk:
                homeworld_1 = await get_data([person_data['homeworld']], 'name', session_deep)
                films_1 = await get_data(person_data['films'], 'title', session_deep)
                species_1 = await get_data(person_data['species'], 'name', session_deep)
                starships_1 = await get_data(person_data['starships'], 'name', session_deep)
                vehicles_1 = await get_data(person_data['vehicles'], 'name', session_deep)
                newperson = PersonModel(
                    birth_year=person_data['birth_year'],
                    eye_color=person_data['eye_color'],
                    films=films_1,
                    gender=person_data['gender'],
                    hair_color=person_data['hair_color'],
                    height=person_data['height'],
                    homeworld=homeworld_1,
                    mass=person_data['mass'],
                    name=person_data['name'],
                    skin_color=person_data['skin_color'],
                    species=species_1,
                    starships=starships_1,
                    vehicles=vehicles_1,
                )
                session.add(newperson)
                await session.commit()


async def get_person(person_id: int, session: ClientSession):
    print(f'begin {person_id}')
    async with session.get(f'https://swapi.dev/api/people/{person_id}') as response:
        person = await response.json()
        print(f'end {person_id}')
        return person


async def get_people():
    async with ClientSession() as session:
        for id_chunk in chunked(range(1, PEOPLE_COUNT), CHUNK_SIZE):
            coroutines = [get_person(i, session=session) for i in id_chunk]
            people = await asyncio.gather(*coroutines)
            for item in people:
                yield item


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()
    async for chunk in async_chunk(get_people(), CHUNK_SIZE):
        asyncio.create_task(people_insertion(chunk))
    tasks = set(asyncio.all_tasks()) - {asyncio.current_task()}
    for task in tasks:
        await task


if __name__ == '__main__':
    start = datetime.now()
    asyncio.run(main())
    print(datetime.now() - start)