import asyncio
import logging
import time
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from db import Sqlite
from states import Searchstudent, Student, Lesson, Deletestudent, Deletelesson, Getstudent, Change, Searchstudent, PaymentList, ChangeLesson
import cfg
from db import Sqlite
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
import timer
from datetime import datetime
from buttons import menu, allkb, edit_menu, exit_menu, yesnomenu
from aiogram.utils.markdown import hbold
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()


logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=cfg.TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)
db = Sqlite('morze.db')
button_list = []

months = {
    1: 'Январь',
    2: "Февраль",
    3: 'Март',
    4: 'Апрель',
    5: 'Май',
    6: 'Июнь',
    7: 'Июль',
    8: 'Август',
    9: 'Сентябрь',
    10: 'Октябрь',
    11: 'Ноябрь',
    12: 'Декабрь',
}

@dp.message_handler(text='📋Главное меню')
async def main_menu(message: types.Message):
    if message.from_user.id in cfg.admins:
        await message.answer('Главное меню', reply_markup=menu)

@dp.message_handler(commands='start')
async def startmessage(message: types.Message):
    if message.from_user.id in cfg.admins:
        await message.answer('Старт', reply_markup=menu)
    else:
        await message.answer('Вы не админ!')
       
@dp.message_handler(state="*",text='⬅️Назад')
async def next(message: types.Message, state: FSMContext):
    await message.answer('Главное меню', reply_markup=menu)
    await state.finish()

async def scheduled(wait_for):
    # schedule.every().day.at("09:00").do(sendeveryday)
    while True:
        # await schedule.run_pending()
        # await asyncio.sleep(1)
        await asyncio.sleep(wait_for)
        now = timer.now_to_time(datetime.now().strftime('%d.%m.%Y'))
        for v in db.get_student():
            
            tt = timer.str_to_time(v[3])
            if now == tt:
                for ax in cfg.admins:
                    await bot.send_message(chat_id=ax, text=f'{v[1]} по {v[2]} должен {v[3]} заплатить {v[4]} сумм')
                
                one_month = timer.plus_one_month(v[3])
                only_month = timer.plus_one_month_only(v[3])
                db.updetenotpay(name=v[1], month=only_month)
                db.update_time(name=v[1], time=one_month)

        
async def sendeveryday():
    for v in db.getnotpay():
        for ax in cfg.admins:
            await bot.send_message(chat_id=ax, text=f'{hbold(v[1])} За {hbold(months[v[2]])} По предмету {hbold(v[3])} Должен {hbold(v[4])}' )


######################################################## ADD STUDENT ###############################################################################

@dp.message_handler(text='👤Добавить ученика')
async def addstudent(message: types.Message):
    if message.from_user.id in cfg.admins:
        await message.answer('Введите имя ученика.', reply_markup=exit_menu)
        await Student.name.set()

@dp.message_handler(state = Student.name)
async def addstudent_name_state(message: types.Message, state: FSMContext):
    await state.update_data(name = message.text)
    for button in db.get_lesson():
        button_list.append(KeyboardButton(button[0]))
    button_list.append(KeyboardButton('⬅️Назад'))
    button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
    await message.answer('Введите имя предмета', reply_markup=button_menu)
    button_list.clear()
    await Student.lesson.set() 

@dp.message_handler(state = Student.lesson)
async def addstudent_lesson_state(message: types.Message, state: FSMContext):
    await state.update_data(lesson = message.text)
    await message.answer('Введите дату оплаты')
    await Student.date.set()

@dp.message_handler(state=Student.date)
async def addstudent_date_state(message: types.Message, state: FSMContext):
    try: 
        datetime.strptime(f'{message.text} 12:37.00', '%d.%m.%Y %H:%M.%S')
        await state.update_data(date = message.text)
        await message.answer('Введите цену оплаты')
        await Student.price.set()
    except:
        await message.answer('Вы ввели не правильный формат времени, введите время в виде дд.мм.ггггг')
    

@dp.message_handler(state=Student.price)
async def addstudent_price_state(message: types.Message, state: FSMContext):
    await state.update_data(price = message.text)
    now = timer.now_to_time(datetime.now().strftime('%d.%m.%Y'))
    data = await state.get_data()
    tt = timer.str_to_time(data['date'])
    month = timer.get_month(data['date'])
    db.add_student(name= data['name'],lesson= data['lesson'],date= data['date'],price= data['price'])
    if now > tt:
        db.insertnotpayment(name=data['name'], month=month, lesson=data['lesson'], price=data['price'])
    await message.answer('Готово!', reply_markup=allkb)
    await state.finish()

######################################################## ADD GROUP ###############################################################################

@dp.message_handler(text='📚Добавить группу')
async def addgroup(message: types.Message):
    if message.from_user.id in cfg.admins:
        await message.answer('Отправьте название предмета')
        await Lesson.lesson.set()

@dp.message_handler(state=Lesson.lesson)
async def addgroup_state(message: types.Message, state: FSMContext):
    db.add_group(message.text)
    await message.answer('Готово', reply_markup=allkb)
    await state.finish()

######################################################## DELETE STUDENT ###############################################################################

@dp.message_handler(text='❌Удалить ученика')
async def deletestudent(message: types.Message):
    if message.from_user.id in cfg.admins:
        for button in db.get_lesson():
            button_list.append(KeyboardButton(button[0]))
        button_list.append(KeyboardButton('⬅️Назад'))
        button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
        await message.answer('Выберите предмет.', reply_markup=button_menu)
        button_list.clear()
        await Deletestudent.lesson.set()

@dp.message_handler(state=Deletestudent.lesson)
async def deletestudent_state(message: types.Message, state: FSMContext):
    if db.get_student_by_lesson(message.text):
        with open('students.txt', 'w') as file:
            for text in db.get_student_by_lesson(message.text):
                file.write(f'{text[0]}. {text[1]}\n')
                button_list.append(KeyboardButton(text[0]))
            button_list.append(KeyboardButton('⬅️Назад'))
            button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
        with open('students.txt', 'r') as file:
            msg = file.read()
            await message.answer(msg, reply_markup=button_menu)
            await message.answer("Выберите уеника")
            button_list.clear()
            await Deletestudent.id.set()
        with open('students.txt', 'w') as file:
            file.write('')

@dp.message_handler(state=Deletestudent.id)
async def deletestudent_state_id(message: types.Message, state: FSMContext):
    print(message.text)
    db.delete_student(message.text)
    await message.answer('Готово', reply_markup=allkb)
    await state.finish()

######################################################## GET STUDENT ###############################################################################

@dp.message_handler(text="📄Список всех учеников")
async def getstudent(message: types.Message):
    if message.from_user.id in cfg.admins:
        for button in db.get_lesson():
                button_list.append(KeyboardButton(button[0]))
        button_list.append(KeyboardButton('⬅️Назад'))
        button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
        await message.answer('Выберите предмет.', reply_markup=button_menu)
        button_list.clear()
        await Getstudent.lesson.set()

@dp.message_handler(state=Getstudent.lesson)
async def sendlist(message: types.Message, state: FSMContext):
    for text in db.get_student_by_lesson(message.text):
        await message.answer(f'{hbold("Имя:")} {text[1]}\n{hbold("След. дата оплаты:")} {text[3]}\n{hbold("Цена оплаты:")} {text[4]}\n', reply_markup=allkb) 
    await state.finish()

@dp.message_handler(text='✏️Изменить информацию о учениках')
async def edit_student(message: types.Message):
    if message.from_user.id in cfg.admins:
        for button in db.get_lesson():
                button_list.append(KeyboardButton(button[0]))
        button_list.append(KeyboardButton('⬅️Назад'))
        button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
        await message.answer('Выберите предмет.', reply_markup=button_menu)
        button_list.clear() 
        await Change.lesson.set()

@dp.message_handler(state=Change.lesson)
async def edit_student2(message: types.Message, state: FSMContext):
    await state.update_data(lesson=message.text)
    if db.get_student_by_lesson(message.text):
        with open('students.txt', 'w') as file:
            for text in db.get_student_by_lesson(message.text):
                file.write(f'{text[0]}. {text[1]}\n')
                button_list.append(KeyboardButton(text[0]))
            button_list.append(KeyboardButton('⬅️Назад'))
            button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
        with open('students.txt', 'r') as file:
            msg = file.read()
            await message.answer(msg, reply_markup=button_menu)
            await message.answer("Выберите уеника")
            button_list.clear()
            await Change.id.set()
        with open('students.txt', 'w') as file:
            file.write('')
    else:
        await message.answer('Введённый вами группа не найдена, или вы ещё не добавили в групп ')

@dp.message_handler(state=Change.id)
async def edit_student3(message: types.Message, state: FSMContext):
    await state.update_data(studentid = message.text)
    await message.answer('Выберите действие', reply_markup=edit_menu)
    await Change.choice.set()

@dp.message_handler(state=Change.choice)
async def edit_student4(message: types.Message, state: FSMContext):
    if message.text == '👤Изменить имя':
        user = await state.get_data()
        for student in db.get_student_by_id(int(user['studentid'])):
            await message.answer(f'{hbold("Текущее значение")}: {student[1]}\nВведите новое значение')
        await Change.name.set()
    if message.text == '🗓Изменить дату':
        user = await state.get_data()
        for student in db.get_student_by_id(int(user['studentid'])):
            await message.answer(f'{hbold("Текущее значение")}: {student[3]}\nВведите новое значение')
        await Change.date.set()
    if message.text == '💰Изменить цену':
        user = await state.get_data()
        for student in db.get_student_by_id(int(user['studentid'])):
            await message.answer(f'{hbold("Текущее значение")}: {student[4]}\nВведите новое значение')
        await Change.price.set()
    if message.text == '📚Изменить группу':
        user = await state.get_data()
        for student in db.get_student_by_id(int(user['studentid'])):
            await message.answer(f'{hbold("Текущее значение")}: {student[2]}\nВведите новое значение')
        await Change.new_lesson.set()

@dp.message_handler(state= Change.name)
async def edit_name(message: types.Message, state: FSMContext):
    user = await state.get_data()
    db.edit_name(id=int(user['studentid']), name=message.text)
    await message.answer('Готово', reply_markup=allkb)
    await state.finish()

@dp.message_handler(state= Change.date)
async def edit_date(message: types.Message, state: FSMContext):
    user = await state.get_data()
    try: 
        datetime.strptime(f'{message.text} 12:37.00', '%d.%m.%Y %H:%M.%S')
        db.edit_date(id=int(user['studentid']), date=message.text)
        await message.answer('Готово', reply_markup=allkb)
        await state.finish()
    except:
        await message.answer('Вы ввели не правильный формат времени, введите время в виде дд.мм.ггггг')

@dp.message_handler(state= Change.price)
async def edit_price(message: types.Message, state: FSMContext):
    user = await state.get_data()
    db.edit_price(id=int(user['studentid']), price=message.text)
    await message.answer('Готово', reply_markup=allkb)
    await state.finish()

@dp.message_handler(state= Change.new_lesson)
async def edit_lesson(message: types.Message, state: FSMContext):
    user = await state.get_data()
    db.edit_lesson(id=int(user['studentid']), lesson=message.text)
    await message.answer('Готово', reply_markup=allkb)
    await state.finish()

######################################################## DELETE GROUP ###############################################################################

@dp.message_handler(text='❌Удалить предмет')
async def deletegroup(message: types.Message):
    if message.from_user.id in cfg.admins:
        for button in db.get_lesson():
            button_list.append(KeyboardButton(button[0]))
        button_list.append(KeyboardButton('⬅️Назад'))
        button_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(*button_list)
        await message.answer('Выберите предмет.', reply_markup=button_menu)
        button_list.clear()
        await Deletelesson.name.set()

@dp.message_handler(state= Deletelesson.name)
async def delete_lesson(message: types.Message, state: FSMContext):
    db.delete_lesson_by_name(message.text)
    await message.answer('Готово', reply_markup=allkb)
    await state.finish()



@dp.message_handler(text='🔍Искать ученика по ИФО')
async def search(message: types.Message):
    if message.from_user.id in cfg.admins:
        exit = KeyboardButton('⬅️Назад')
        mmm = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(exit)
        await message.answer('Введите то имя которе вы ввели ранее', reply_markup=mmm)
        await Searchstudent.name.set()

@dp.message_handler(state=Searchstudent.name)
async def searchstudent(message: types.Message, state: FSMContext):
    if db.get_student_by_name(message.text):
        for student in db.get_student_by_name(message.text):
            await message.answer(f'{hbold("Имя:")} {student[1]}\n{hbold("Предмет:")} {student[2]}\n{hbold("Дата след. оплаты")} {student[3]}\n{hbold("Цена оплаты:")} {student[4]}', reply_markup=allkb)
            await state.finish()
    else:
        await message.answer('Такого ученика нет в списке')


@dp.message_handler(text="📄Список должников")
async def notpaymentlist(message: types.Message):
    if message.from_user.id in cfg.admins:
        for button in db.get_lesson():
                button_list.append(KeyboardButton(button[0]))
        button_list.append(KeyboardButton('⬅️Назад'))
        button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
        await message.answer('Выберите предмет.', reply_markup=button_menu)
        button_list.clear()
        await PaymentList.lesson.set()

@dp.message_handler(state=PaymentList.lesson)
async def notpaystate(message: types.Message, state: FSMContext):
    await state.update_data(lesson=message.text)
    paymentstatus = KeyboardButton('✏️Изменить статус оплаты ученика')
    main = KeyboardButton('📋Главное меню')
    paymentmenu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(paymentstatus, main)
    if db.getnotpaybylesson(message.text):
        with open('students.txt', 'w') as file:
            for text in db.getnotpaybylesson(message.text):
                file.write(f'{text[0]}. {text[1]}\n')
        with open('students.txt', 'r') as file:
            msg = file.read()
            await message.answer(msg, reply_markup=paymentmenu)
            await PaymentList.student.set()
            button_list.clear()
        with open('students.txt', 'w') as file:
            file.write('')
    else:
        await message.answer('По данному предмету нет должников')


@dp.message_handler(text='✏️Изменить статус оплаты ученика', state=PaymentList.student)
async def notpaymentuser(message: types.Message, state: FSMContext):
    
    if message.from_user.id in cfg.admins:
        data = await state.get_data()
        if db.getnotpaybylesson(data['lesson']):
            for text in db.getnotpaybylesson(data['lesson']):
                button_list.append(KeyboardButton(text[0]))
            button_list.append(KeyboardButton('⬅️Назад'))
            button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
            await message.answer("Выберите ученика", reply_markup=button_menu)
            await PaymentList.send.set()
        else:
            await message.answer('По данному предмету нет должников')


@dp.message_handler(state= PaymentList.send)
async def changestat2(message: types.Message, state: FSMContext):
    await state.update_data(id=message.text)
    await message.answer(f'{hbold("Текущий статус:")} Неуплочено\nХотите изменить на {hbold("Уплочено")}?', reply_markup=yesnomenu)
    await PaymentList.yesno.set()

@dp.message_handler(state = PaymentList.yesno)
async def chngestat3(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text == "Да":
        db.deletenotpay(data['id'])
        await message.answer('Готово', reply_markup=allkb)
        await state.finish()
    elif message.text == 'Нет':
        await message.answer('Главное меню', reply_markup=menu)
        await state.finish()
       
@dp.message_handler(text='✏️Изменить имя группы')
async def editlesson(message: types.Message):
    if message.from_user.id in cfg.admins:
        for button in db.get_lesson():
                button_list.append(KeyboardButton(button[0]))
        button_list.append(KeyboardButton('⬅️Назад'))
        button_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*button_list)
        await message.answer('Выберите предмет.', reply_markup=button_menu)
        button_list.clear()
        await ChangeLesson.name.set()

@dp.message_handler(state=ChangeLesson.name)
async def changelesson(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите новое название группы")
    await ChangeLesson.new_name.set()

@dp.message_handler(state= ChangeLesson.new_name)
async def changelesson2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db.updatelesson(name=data['name'], new_name=message.text)
    await state.finish()
    await message.answer('Готово', reply_markup=allkb)
scheduler.add_job(sendeveryday, CronTrigger(year="*", month="*", day="*", hour="21", minute="30", second="1"))

if __name__ == '__main__':
    scheduler.start()
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled(1))
    executor.start_polling(dp)
    
    
    # while True:
    #     loop = asyncio.get_event_loop()
    #     loop.run_until_complete(schedule.run_pending())
    #     time.sleep(0.1)
