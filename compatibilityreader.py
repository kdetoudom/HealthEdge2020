import pandas as pd
import xlrd
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--matrix', type=str, default='HE_Product_Compatibility_18X_AND_ABOVE - Copy.xlsm',
                    help='path to the compatibility matrix in excel')
parser.add_argument('--compatibility-result-file', type=str, default='compatibility.csv',
                    help='compatibility csv table that is generated by this program')
parser.add_argument('--product-list', default='product_list.csv', help='product list csv table')
parser.add_argument('--release-status', default='release_status.csv', help='release status csv table')
parser.add_argument('--product-version-start-id', type=int, default=1,
                    help='first available product_versionID key in database. '
                         'This should not be 1 if there is already data entered')
parser.add_argument('--product-version-result-file', type=str, default='product_version.csv',
                    help='product version csv that is generated by this program')


def str_products(df_product_list: pd.DataFrame):
    s = 'productID: product_name\n'
    for i, row in df_product_list.iterrows():
        s += f'{row["productID"]}: {row["product_name"]}\n'
    return s


def main():
    args = parser.parse_args()
    matrix = xlrd.open_workbook(args.matrix)
    df_product_list = pd.read_csv(args.product_list)
    product_list_str = str_products(df_product_list)
    sheet: xlrd.sheet.Sheet = matrix.sheets()[0]

    # product versions data frame
    df_product_versions = pd.DataFrame(columns=['productID', 'version_number', 'release_status', 'release_date'])
    # create a release status data frame from hard coded dictionary
    df_release_status = pd.read_csv(args.release_status)
    """
    We will iterate over the top columns to get all of the primary comparison product
    For each column, there is a version number, release status, and release date.
    Each of these will be stored in our primary product table.
    """
    start_col = 3
    raw_primary_version_numbers = sheet.row_values(2, start_col)
    raw_primary_release_statuses = sheet.row_values(3, start_col)
    raw_primary_release_dates = sheet.row_values(4, start_col)
    print('The following is a list of product ids. Use it to answer the question below.')
    print(product_list_str)
    primary_product_id = int(input('What is the product id of the horizontal axis (primary product id)? '))

    # this keeps track of the product index
    # we will reuse this for the secondary products too to append them to the product version data frame
    index = args.product_version_start_id
    primary_product_entries = {
        'productID': [],
        'version_number': [],
        'release_status': [],
        'release_date': [],
    }
    indices = []
    for i in range(len(raw_primary_version_numbers)):
        if raw_primary_release_statuses[i] not in df_release_status['abbreviation'].tolist():
            break
        primary_product_entries['productID'].append(primary_product_id)
        primary_product_entries['version_number'].append(str(raw_primary_version_numbers[i]))
        primary_product_entries['release_status'].append(str(raw_primary_release_statuses[i]))
        date = xlrd.xldate.xldate_as_tuple(raw_primary_release_dates[i], 0)
        primary_product_entries['release_date'].append(f'{date[0]:04}-{date[1]:02}-{date[2]:02}')
        indices.append(index)
        index += 1

    df_primary_product_versions = pd.DataFrame(primary_product_entries, indices)
    df_product_versions = df_product_versions.append(df_primary_product_versions)

    """
    Here we detect the secondary product ids with the help of the user.
    Every time we detect a product, the following versions numbers pertain to that product.
    """
    start_row = 5
    raw_secondary_product_list = sheet.col_values(0, start_row)
    raw_secondary_release_status = sheet.col_values(1, start_row)
    raw_secondary_release_date = sheet.col_values(2, start_row)

    compatibility_entries = {
        'product_version_ID_1': [],
        'product_version_ID_2': [],
    }

    secondary_product_entries = {
        'productID': [],
        'version_number': [],
        'release_status': [],
        'release_date': [],
    }

    # we iterate over the rows in the matrix to detect each product and compatibilities as we go along
    secondary_indices = []
    secondary_product_id = None
    for i in range(len(raw_secondary_product_list)):
        row = start_row + i
        product_name_or_version_number = str(raw_secondary_product_list[i])
        if product_name_or_version_number == '':
            break
        secondary_release_status = str(raw_secondary_release_status[i])
        if secondary_release_status in df_release_status['abbreviation'].tolist():
            secondary_version_number = product_name_or_version_number
            release_date = raw_secondary_release_date[i]
            if isinstance(release_date, float):
                date = xlrd.xldate.xldate_as_tuple(release_date, 0)
                secondary_release_date = f'{date[0]}-{date[1]:02}-{date[2]:02}'
            else:
                raise ValueError(f'Expected a float for the release date {release_date}. '
                                 f'You can find this on row {row + 1}')
            secondary_product_entries['productID'].append(secondary_product_id)
            secondary_product_entries['version_number'].append(secondary_version_number)
            secondary_product_entries['release_status'].append(secondary_release_status)
            secondary_product_entries['release_date'].append(secondary_release_date)

            # iterate over the compatibilities in the row to get compatibility
            for j, compatibility_value in enumerate(sheet.row_values(row, start_col)):
                col = start_col + j
                if compatibility_value != '':
                    primary_version_number = str(sheet.cell_value(2, col))
                    primary_version_entry = df_primary_product_versions.index[
                        df_primary_product_versions['version_number'] == primary_version_number]
                    primary_version_id = primary_version_entry.tolist()[0]
                    compatibility_entries['product_version_ID_1'].append(primary_version_id)
                    compatibility_entries['product_version_ID_2'].append(index)

            secondary_indices.append(index)
            index += 1
        else:
            # Show the user the list of products ids to choose from
            print('The following is a list of product ids. Use it to answer the question below.')
            print(product_list_str)
            # show the user the current product
            print(f'Detected product name: {product_name_or_version_number}')
            # get the correct id from the user's input
            secondary_product_id = int(input('Which ID does this product belong to from the list provided above? '))

    df_secondary_product_versions = pd.DataFrame(data=secondary_product_entries, index=secondary_indices)
    df_product_versions = df_product_versions.append(df_secondary_product_versions)
    df_compatibility = pd.DataFrame(compatibility_entries)

    df_product_versions['product_version_ID'] = df_product_versions.index
    df_product_versions = pd.merge(df_product_versions, df_release_status, left_on='release_status',
                                   right_on='abbreviation', validate='many_to_one')

    df_compatibility = df_compatibility.sort_values(['product_version_ID_1', 'product_version_ID_2'], ignore_index=True)
    df_compatibility.index += 1
    df_compatibility['compatibilityID'] = df_compatibility.index
    df_compatibility = df_compatibility[['compatibilityID', 'product_version_ID_1', 'product_version_ID_2']]

    df_product_versions = df_product_versions[[
        'product_version_ID', 'productID', 'version_number', 'release_date', 'release_statusID']]
    df_product_versions = df_product_versions.sort_values('product_version_ID')

    df_product_versions.to_csv(args.product_version_result_file, index=False)
    df_compatibility.to_csv(args.compatibility_result_file, index=False)


if __name__ == '__main__':
    main()
