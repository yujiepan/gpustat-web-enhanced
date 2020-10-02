import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
import aiosqlite
import asyncio


def get_date_list(today, days=30):
    date = sorted([(datetime.strptime(today, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
                   for i in range(1, days + 1)])
    return date


class Database():
    def __init__(self, path='usages.db'):
        self.path = path
        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS usages
            (name   VARCHAR(20)    NOT NULL,
            usage   INT            NOT NULL,
            time    DATETIME       NOT NULL);''')
        cursor.execute('''DROP INDEX IF EXISTS name_index;''')
        cursor.execute('''DROP INDEX IF EXISTS time_index;''')
        conn.commit()
        cursor.close()
        conn.close()

    async def clear_async(self, month_like):
        print('=' * 20, month_like, '=' * 20)
        db = await aiosqlite.connect(self.path)
        cursor = await db.execute(f'''
                    SELECT name, SUM(usage) FROM usages
                    WHERE time LIKE '{month_like}_%'
                    GROUP BY name;
                    ''')
        rows = await cursor.fetchall()
        print('Rows to be deleted:', rows)
        await cursor.close()
        await db.close()

        p = [(name, usage, month_like) for name, usage in rows if int(usage) > 0]
        self.insert(p, auto_time=False)

        async with aiosqlite.connect(self.path) as db:
            await db.execute(f'''
                        DELETE FROM usages
                        WHERE time LIKE '{month_like}_%_%'
                        ''')
            await db.commit()

        db = await aiosqlite.connect(self.path)
        cursor = await db.execute(f'''
                    SELECT * FROM usages
                    WHERE time LIKE '{month_like}%'
                    ''')
        rows = await cursor.fetchall()
        print('Now exsiting:', rows)
        await cursor.close()
        await db.close()

        async with aiosqlite.connect(self.path) as db:
            await db.execute('''vacuum;''')
            await db.commit()

        return rows

    def clear(self, months=['2020-05']):
        for month in months:
            asyncio.run(self.clear_async(month))

    async def insert_async(self, name_usage_list=[('test', 1)], auto_time=True):
        async with aiosqlite.connect(self.path) as db:
            if auto_time:
                await db.executemany('''
                    INSERT INTO USAGES (NAME, USAGE, TIME)
                    VALUES (?, ?, datetime('now', 'localtime'));''', name_usage_list)
            else:
                await db.executemany('''
                    INSERT INTO USAGES (NAME, USAGE, TIME)
                    VALUES (?, ?, ?);''', name_usage_list)
            await db.commit()

    def insert(self, name_usage_list=[('user_test', 1)], auto_time=True):
        asyncio.run(self.insert_async(name_usage_list,
                                      auto_time=auto_time))
        print('inserted!')

    async def past_async(self, last_what='-7 days'):
        magic_number = 1.0 / 59.9 / 1024  # GB-h
        db = await aiosqlite.connect(self.path)
        cursor = await db.execute(f'''
                    SELECT name, SUM(usage * {magic_number}  ) FROM usages
                    WHERE time > datetime('now', '{last_what}', 'localtime')
                    GROUP BY name;
                    ''')
        rows = await cursor.fetchall()
        await cursor.close()
        await db.close()
        return rows

    def past(self, last_what='-7 days'):
        '''Returns [(user, usage)] in GB-h.'''
        return asyncio.run(self.past_async(last_what))

    def past_1_hour(self):
        return self.past('-1 hour')

    def past_24_hours(self):
        return self.past('-24 hours')

    def past_3_days(self):
        return self.past('-3 days')

    def past_7_days(self):
        return self.past('-7 days')

    def get_all(self):
        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, usage, time FROM usages;
            ''')
        values = cursor.fetchall()
        cursor.close()
        conn.close()
        return values

    async def search_name_async(self, user):
        """Search the monthly report."""
        magic_number = 1.0 / 59.9 / 1024  # GB-h
        db = await aiosqlite.connect(self.path)
        cursor = await db.execute(f'''
                SELECT name, date(time), sum(usage * {magic_number} )
                FROM usages
                WHERE name = ? AND time > datetime("now", "-31 days")
                GROUP BY name, date(time);''', (user.strip(),))
        rows = await cursor.fetchall()
        await cursor.close()
        await db.close()
        return rows

    def search_name(self, user):
        return asyncio.run(self.search_name(user))

    def summary(self, user):
        raw = self.search_name(user.strip())
        date_l = get_date_list(str(date.today()))
        res = defaultdict(float)
        for d in date_l:
            res[d] = 0
        for (user, d, usage) in raw:
            res[d] = usage
        return res


if __name__ == "__main__":
    import time
    t = time.time()
    db = Database()
    db.clear([f'2020-{m:02d}' for m in range(4, 8)])
    print(time.time() - t)
