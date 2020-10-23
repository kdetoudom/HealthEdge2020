import pandas as pd
import argparse
import mysql.connector
from mysql.connector.cursor import MySQLCursor

parser = argparse.ArgumentParser()
# If database moves to a new serve, the username and password should be changed
parser.add_argument('--user', type=str, default='root', help='username for connection to SQL')
parser.add_argument('--password', type=str, required=True, help='type in the password')
parser.add_argument('--save-path', type=str, default=None, help='save commands to file')


def show_products(cursor: MySQLCursor):
    """
    Displays a list of all the products included in the database with their productID
    :param cursor: mySQL
    """
    cursor.execute(r'SELECT productID, product_name FROM product_list;')
    results = cursor.fetchall()
    print('\nCurrent product list:')
    print('productID: product_name')
    for productID, product_name in results:
        print(f'{productID}: {product_name}')


def show_product_versions(cursor: MySQLCursor, productID):
    """
    Displays all the product versions of a specified product that the user chooses
    :param cursor: mySQL cursor
    :param productID: The unique ID number for a product
    """
    query = '''SELECT product_version_ID, version_number, release_date, description
FROM product_versions,
     release_status_key
WHERE productID = {}
  AND product_versions.release_statusID = release_status_key.release_statusID;
'''.format(productID)
    cursor.execute(query)
    results = cursor.fetchall()
    print(f'\nProduct versions filtered by productID={productID}:')
    print('product_version_ID, version_number, release_date, description')
    for row in results:
        print('{}, {}, {}, {}'.format(*row))


def show_release_status_keys(cursor: MySQLCursor):
    """
    Displays the release_status table
    :param cursor: mySQL
    """
    cursor.execute('SELECT * FROM release_status_key')
    print('\nRelease status table')
    print('release_statusID, abbreviation, description')
    for row in cursor.fetchall():
        print('{}, {}, {}'.format(*row))


def show_compatibility(cursor: MySQLCursor, product_name, version_number):
    """
    Shows a list of compatible product versions of the product and version that the user has inputted
    :param cursor: mySQL
    :param product_name: The name of the product the user wants to find compatibility for
    :param version_number: The version of the specified product the user wants to find compatibility for
    """
    query = f'''
SELECT pv2.product_version_ID AS 'Product Version ID',
       pl2.product_name   AS 'Product Name',
       pv2.version_number AS 'Version Number',
       pv2.release_date   AS 'Release Date',
       rskey.description  AS 'Release Status'
FROM product_list AS pl2,
     product_versions AS pv2,
     release_status_key AS rskey
WHERE pl2.productID = pv2.productID
    AND rskey.release_statusID = pv2.release_statusID
    AND (pv2.product_version_ID IN (
        SELECT compatibility.product_version_ID_2
        FROM compatibility
        WHERE compatibility.product_version_ID_1 = (
            SELECT product_versions.product_version_ID
            FROM product_list,
                 product_versions
            WHERE product_versions.version_number = '{version_number}'
                AND product_list.product_name = '{product_name}'
                AND product_list.productID = product_versions.productID
        )
    )
    OR pv2.product_version_ID IN (
        SELECT compatibility.product_version_ID_1
        FROM compatibility
        WHERE compatibility.product_version_ID_2 = (
            SELECT product_versions.product_version_ID
            FROM product_list,
                 product_versions
            WHERE product_versions.version_number = '{version_number}'
                AND product_list.product_name = '{product_name}'
                AND product_list.productID = product_versions.productID
        )
    )
);'''
    cursor.execute(query)
    print('\nCompatibilities:')
    print('product_version_ID, Product Name, Version Number, Release Date, Release Status')
    for row in cursor.fetchall():
        print('{}, {}, {}, {}, {}'.format(*row))

    query = f'''SELECT product_versions.product_version_ID
                FROM product_list,
                     product_versions
                WHERE product_versions.version_number = '{version_number}'
                    AND product_list.product_name = '{product_name}'
                    AND product_list.productID = product_versions.productID'''
    cursor.execute(query)
    print('query product_version_ID:')
    for row in cursor.fetchall():
        print(row[0])


def edit_product(cursor: MySQLCursor):
    """
    Edits a product by either adding a new product or renaming a pre-existing product
    :param cursor: mySQL
    :return: SQL command to change/add the product
    """
    show_products(cursor)

    selection = input('\nWhat do you wish to do?\n'
                      '1: add new product\n'
                      '2: rename product\n'
                      'anything else: cancel edit\n')
    command = None
    if selection == '1':
        product_name = input('enter a product name: ')
        # productID is automatically generated
        command = f'INSERT INTO product_list (product_name) ' \
                  f'VALUES ({product_name});'
    elif selection == '2':
        productID = input('enter a productID: ')
        if not productID.isnumeric():
            print('entered invalid productID')
            return None
        product_name = input('enter a product_name: ')
        command = f'UPDATE product_list ' \
                  f'SET product_name={product_name} ' \
                  f'WHERE productID={productID};'
    return command


def edit_product_version(cursor: MySQLCursor):
    """
    Can either display a specified product and its version or add/update the product's version
    :param cursor: MySQL
    :return: SQL command to add/update product version
    """
    selection = input('\nWhat do you wish to do?\n'
                      '1: view product versions\n'
                      '2: add new product version\n'
                      '3: update product version\n'
                      'anything else: cancel edit\n')
    command = None
    if selection == '1':
        show_products(cursor)
        productID = input('Select a productID: ')
        show_product_versions(cursor, productID)
    elif selection == '2':
        show_products(cursor)
        productID = input('Select a productID: ')
        version_number = input('Enter a version number: ')
        release_date = input('Enter a release date (yyyy-mm-dd): ')
        show_release_status_keys(cursor)
        release_statusID = input('Select a release_statusID: ')
        command = f'INSERT INTO (productID, version_number, release_date, release_statusID) ' \
                  f'VALUES ({productID}, {version_number}, {release_date}, {release_statusID});'
    elif selection == '3':
        product_version_ID = input('enter a product_version_ID: ')
        if not product_version_ID.isnumeric():
            print('did not provide proper product_version_ID')
            return None
        productID = input('Select a productID (blank = no change): ')
        version_number = input('Enter a version number (blank = no change): ')
        release_date = input('Enter a release date (yyyy-mm-dd) (blank = no change): ')
        show_release_status_keys(cursor)
        release_statusID = input('Select a release_statusID (blank = no change): ')

        values = []
        if productID != '':
            values.append(f'productID={productID}')
        if version_number != '':
            values.append(f'version_number={version_number}')
        if release_date != '':
            values.append(f'release_date={release_date}')
        if release_statusID != '':
            values.append(f'release_statusID={release_statusID}')
        if len(values) == 0:
            print('no values changed!')
            return None
        columns = values[0]
        for v in values[1:]:
            columns += ', ' + v
        command = f'UPDATE product_version ' \
                  f'SET {columns} ' \
                  f'WHERE product_version_ID={product_version_ID};'

    return command


def edit_compatibility(cursor: MySQLCursor):
    """
    Can either show compatibility for a specific product version or add new product version compatibility
    :param cursor: mySQL
    :return: SQL command
    """
    command = None
    selection = input('\nWhat do you wish to do?\n'
                      '1: view compatibilities\n'
                      '2: add new compatibility\n'
                      'anything else: cancel edit\n')
    if selection == '1':
        product_name = input('Enter a product name: ')
        version_number = input('Enter a version_number: ')
        show_compatibility(cursor, product_name, version_number)
    elif selection == '2':
        product_version_ID_1 = input('Enter the first product_version_ID: ')
        product_version_ID_2 = input('Enter the second product_version_ID: ')
        command = f'INSERT INTO compatibility (product_version_ID_1, product_version_ID_2) ' \
                  f'VALUES ({product_version_ID_1}, {product_version_ID_2})'
    return command


def main():
    """
    Main function that prompts the user by asking what they would like to do. When the user selects a task to complete
    they run the corresponding function
    """
    args = parser.parse_args()
    mydb = mysql.connector.connect(
        host="localhost",
        user=args.user,
        password=args.password,
        database='productcompatibilitymatrix',
    )
    cursor = mydb.cursor()
    command_list = []
    while True:
        choice = input('\nWhich do you wish to do?\n'
                       '1: edit product list table\n'
                       '2: edit product version table\n'
                       '3: edit compatibility table\n'
                       '4: show commands\n'
                       'q: quit\n')
        command = None
        if choice == 'q':
            break
        elif choice == '1':
            command = edit_product(cursor)
        elif choice == '2':
            command = edit_product_version(cursor)
        elif choice == '3':
            command = edit_compatibility(cursor)
        elif choice == '4':
            print('Your commands:')
            for c in command_list:
                print(c)
        else:
            print('Wrong input. Try entering "1", "2", "3", "4", or "q"')

        if command is not None:
            print(f'Your command: \n{command}\n')
            command_list.append(command)

    print('Your final command list:')
    for command in command_list:
        print(command)

    if args.save_path is not None:
        with open(args.save_path, mode='w') as f:
            f.writelines(command_list)
        print(f'saved commands to {args.save_path}')


if __name__ == '__main__':
    main()
